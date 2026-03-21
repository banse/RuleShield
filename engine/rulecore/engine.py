"""RuleEngine — the main entry point for rulecore."""
from __future__ import annotations

import logging
from typing import Any

from rulecore.types import ScoringConfig, MatchResult
from rulecore.scoring import compute_confidence_level
from rulecore.conditions import evaluate_condition_tree, resolve_field, get_regex
from rulecore.loader import load_rules, save_state

logger = logging.getLogger("rulecore.engine")


class RuleEngine:
    """Generic pattern-matching rule engine with weighted scoring."""

    def __init__(
        self,
        rules_dir: str = "",
        scoring: ScoringConfig | None = None,
        bundled_dir: str | None = None,
    ) -> None:
        self.rules_dir = rules_dir
        self.scoring = scoring or ScoringConfig()
        self.bundled_dir = bundled_dir
        self.rules: list[dict[str, Any]] = []
        self.deactivation_threshold: float = 0.5
        self._dirty = False
        self._match_count_since_save = 0
        self._save_interval = 100

    def load(self) -> None:
        if self.rules_dir:
            self.rules = load_rules(self.rules_dir, self.bundled_dir)

    def match(
        self,
        context: dict[str, Any],
        confidence_threshold: float = 0.0,
        deployment: str = "production",
    ) -> MatchResult | None:
        return self._match_with_scope(context, confidence_threshold, deployment, "hit_count")

    def match_candidates(
        self,
        context: dict[str, Any],
        confidence_threshold: float = 0.0,
    ) -> MatchResult | None:
        return self._match_with_scope(context, confidence_threshold, "candidate", "shadow_hit_count")

    def _match_with_scope(
        self,
        context: dict[str, Any],
        confidence_threshold: float,
        deployment: str,
        hit_field: str,
    ) -> MatchResult | None:
        best: dict[str, Any] | None = None
        best_score: float = 0.0
        best_priority: int | None = None

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            if rule.get("deployment", "production") != deployment:
                continue
            rule_confidence = float(rule.get("confidence", 1.0))
            if rule_confidence < self.deactivation_threshold:
                continue
            if rule_confidence < confidence_threshold:
                continue
            rule_priority = rule.get("priority", 0)
            if best is not None and rule_priority < best_priority:
                break

            if "condition_tree" in rule:
                passed, score, matched_kw, matched_pat = evaluate_condition_tree(
                    rule["condition_tree"], context, self.scoring,
                )
                if not passed or score < self.scoring.min_score:
                    continue
            else:
                score, matched_kw, matched_pat = self._score_flat_rule(rule, context)
                if score < self.scoring.min_score:
                    continue

            if score > best_score:
                has_keywords = len(matched_kw) > 0
                has_patterns = len(matched_pat) > 0
                confidence_level = compute_confidence_level(score, has_keywords, has_patterns)
                best_score = score
                best_priority = rule_priority
                best = {
                    "rule": rule,
                    "score": score,
                    "kw": matched_kw,
                    "pat": matched_pat,
                    "level": confidence_level,
                }

        if best is None:
            return None

        winning_rule = best["rule"]
        winning_rule[hit_field] = winning_rule.get(hit_field, 0) + 1
        self._dirty = True
        self._match_count_since_save += 1
        if self._match_count_since_save >= self._save_interval and self.rules_dir:
            save_state(self.rules, self.rules_dir)
            self._dirty = False
            self._match_count_since_save = 0

        return MatchResult(
            rule_id=winning_rule["id"],
            rule_name=winning_rule.get("name", winning_rule["id"]),
            response=winning_rule["response"],
            confidence=winning_rule.get("confidence", 1.0),
            match_score=best["score"],
            confidence_level=best["level"],
            matched_keywords=best["kw"],
            matched_patterns=best["pat"],
            deployment=winning_rule.get("deployment", "production"),
        )

    def _score_flat_rule(
        self, rule: dict[str, Any], context: dict[str, Any],
    ) -> tuple[float, list[str], list[str]]:
        for cond in rule.get("conditions", []):
            ctype = cond.get("type", "")
            cvalue = cond.get("value", 0)
            raw = resolve_field(cond.get("field", ""), context)
            field_text = str(raw) if raw != "" else ""
            if ctype == "max_length" and len(field_text) > int(cvalue):
                return (0.0, [], [])
            if ctype == "min_length" and len(field_text) < int(cvalue):
                return (0.0, [], [])
            if ctype in ("max_messages", "max_value"):
                numeric = int(raw) if isinstance(raw, (int, float)) else 0
                if numeric > int(cvalue):
                    return (0.0, [], [])

        score = 0.0
        matched_kw: list[str] = []
        matched_pat: list[str] = []

        for pat in rule.get("patterns", []):
            ptype = pat.get("type", "contains")
            value = pat.get("value", "")
            raw = resolve_field(pat.get("field", ""), context)
            field_text = str(raw) if raw != "" else ""
            text_lower = field_text.lower()
            value_lower = str(value).lower()

            if ptype in ("contains", "startswith"):
                if ptype == "contains" and value_lower in text_lower:
                    score += self.scoring.keyword_weight
                    matched_kw.append(value)
                elif ptype == "startswith" and text_lower.startswith(value_lower):
                    score += self.scoring.keyword_weight
                    matched_kw.append(value)
            elif ptype == "regex":
                try:
                    if get_regex(value).search(field_text):
                        score += self.scoring.pattern_weight
                        matched_pat.append(value)
                except Exception:
                    pass
            elif ptype == "exact":
                if value_lower == text_lower:
                    score += self.scoring.exact_weight
                    matched_pat.append(value)

        if score > 0:
            conditions = rule.get("conditions", [])
            if conditions:
                score += len(conditions) * self.scoring.condition_weight

        return (score, matched_kw, matched_pat)

    def add_rule(self, rule: dict[str, Any]) -> None:
        rule.setdefault("enabled", True)
        rule.setdefault("hit_count", 0)
        rule.setdefault("shadow_hit_count", 0)
        rule.setdefault("confidence", 0.9)
        rule.setdefault("priority", 0)
        rule.setdefault("deployment", "production")
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

    def update_confidence(self, rule_id: str, new_confidence: float) -> bool:
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["confidence"] = max(0.0, min(1.0, new_confidence))
                self._dirty = True
                return True
        return False

    def deactivate_rule(self, rule_id: str) -> bool:
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = False
                self._dirty = True
                return True
        return False

    def activate_rule(self, rule_id: str) -> bool:
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = True
                rule["deployment"] = "production"
                self._dirty = True
                return True
        return False

    def get_active_rules(self) -> list[dict[str, Any]]:
        return [
            {
                "id": r["id"],
                "name": r.get("name", r["id"]),
                "deployment": r.get("deployment", "production"),
                "enabled": r.get("enabled", True),
                "priority": r.get("priority", 0),
                "hit_count": r.get("hit_count", 0),
                "shadow_hit_count": r.get("shadow_hit_count", 0),
                "confidence": r.get("confidence", 1.0),
                "pattern_count": len(r.get("patterns", [])),
                "has_condition_tree": "condition_tree" in r,
            }
            for r in self.rules
            if r.get("enabled", True)
        ]

    def get_stats(self) -> dict[str, Any]:
        active = [r for r in self.rules if r.get("enabled", True)]
        total_hits = sum(r.get("hit_count", 0) for r in self.rules)
        top = sorted(self.rules, key=lambda r: r.get("hit_count", 0), reverse=True)[:5]
        return {
            "total_rules": len(self.rules),
            "active_rules": len(active),
            "total_hits": total_hits,
            "top_rules": [
                {"id": r["id"], "name": r.get("name", r["id"]), "hit_count": r.get("hit_count", 0)}
                for r in top
            ],
        }
