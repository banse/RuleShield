"""FeedbackManager — bandit-style confidence tuning with analytics for rulecore."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from rulecore.types import FeedbackEntry, RuleEvent

logger = logging.getLogger("rulecore.feedback")


class _EngineProtocol(Protocol):
    rules: list[dict[str, Any]]
    def update_confidence(self, rule_id: str, new_confidence: float) -> bool: ...
    def deactivate_rule(self, rule_id: str) -> bool: ...
    def activate_rule(self, rule_id: str) -> bool: ...


class _StoreProtocol(Protocol):
    def save_feedback(self, entry: FeedbackEntry) -> None: ...
    def save_event(self, event: RuleEvent) -> None: ...
    def load_feedback(self, rule_id: str | None = None) -> list[FeedbackEntry]: ...


class FeedbackManager:
    """Bandit-style confidence updater with analytics."""

    def __init__(
        self,
        engine: Any,
        store: Any,
        acceptance_delta: float = 0.01,
        rejection_delta: float = 0.05,
        deactivation_threshold: float = 0.5,
        promotion_threshold: float = 0.98,
    ) -> None:
        self.engine = engine
        self.store = store
        self.acceptance_delta = acceptance_delta
        self.rejection_delta = rejection_delta
        self.deactivation_threshold = deactivation_threshold
        self.promotion_threshold = promotion_threshold

    def accept(
        self, rule_id: str, prompt: str, *,
        classification_correct: bool | None = None,
        response_helpful: bool | None = None,
        confidence_appropriate: bool | None = None,
    ) -> None:
        entry = FeedbackEntry(
            rule_id=rule_id, prompt=prompt, feedback_type="accept",
            classification_correct=classification_correct,
            response_helpful=response_helpful,
            confidence_appropriate=confidence_appropriate,
        )
        self.store.save_feedback(entry)
        self._update_confidence(rule_id, accepted=True)
        self._check_thresholds()
        logger.debug("Recorded accept for rule %s", rule_id)

    def reject(
        self, rule_id: str, prompt: str, correction: str | None = None, *,
        classification_correct: bool | None = None,
        response_helpful: bool | None = None,
        confidence_appropriate: bool | None = None,
    ) -> None:
        entry = FeedbackEntry(
            rule_id=rule_id, prompt=prompt, feedback_type="reject",
            correction=correction,
            classification_correct=classification_correct,
            response_helpful=response_helpful,
            confidence_appropriate=confidence_appropriate,
        )
        self.store.save_feedback(entry)
        self._update_confidence(rule_id, accepted=False)
        self._check_thresholds()
        logger.debug("Recorded reject for rule %s", rule_id)

    def _update_confidence(self, rule_id: str, accepted: bool) -> None:
        rule = self._find_rule(rule_id)
        if rule is None:
            return
        current = rule.get("confidence", 1.0)
        if accepted:
            new_conf = current + self.acceptance_delta * (1.0 - current)
        else:
            new_conf = current - self.rejection_delta * current
        new_conf = max(0.0, min(1.0, new_conf))
        self.engine.update_confidence(rule_id, new_conf)
        delta = new_conf - current
        direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
        self.store.save_event(RuleEvent(
            rule_id=rule_id, event_type="confidence_update",
            direction=direction, old_confidence=current,
            new_confidence=new_conf, delta=delta,
        ))

    def _check_thresholds(self) -> list[str]:
        deactivated = []
        for rule in self.engine.rules:
            conf = rule.get("confidence", 1.0)
            rid = rule.get("id", "")
            if conf < self.deactivation_threshold and rule.get("enabled", True):
                self.engine.deactivate_rule(rid)
                deactivated.append(rid)
                self.store.save_event(RuleEvent(
                    rule_id=rid, event_type="rule_deactivated",
                    direction="down", old_confidence=conf, new_confidence=conf,
                ))
                logger.warning("Rule %s deactivated (confidence %.4f)", rid, conf)
        return deactivated

    def _find_rule(self, rule_id: str) -> dict[str, Any] | None:
        for rule in self.engine.rules:
            if rule.get("id") == rule_id:
                return rule
        return None

    def get_underperforming_rules(self, min_feedback: int = 5) -> list[dict[str, Any]]:
        all_feedback = self.store.load_feedback()
        per_rule: dict[str, dict[str, int]] = {}
        for fb in all_feedback:
            if fb.rule_id not in per_rule:
                per_rule[fb.rule_id] = {"accept": 0, "reject": 0}
            if fb.feedback_type == "accept":
                per_rule[fb.rule_id]["accept"] += 1
            else:
                per_rule[fb.rule_id]["reject"] += 1
        results = []
        for rid, counts in per_rule.items():
            total = counts["accept"] + counts["reject"]
            if total < min_feedback:
                continue
            rate = counts["accept"] / total if total > 0 else 0.0
            if rate >= 0.70:
                continue
            rule = self._find_rule(rid)
            results.append({
                "rule_id": rid,
                "rule_name": rule.get("name", rid) if rule else rid,
                "accept_count": counts["accept"],
                "reject_count": counts["reject"],
                "total_feedback": total,
                "acceptance_rate": round(rate, 4),
                "current_confidence": rule.get("confidence", 1.0) if rule else None,
            })
        results.sort(key=lambda r: r["acceptance_rate"])
        return results

    def get_performance_by_category(self) -> dict[str, dict[str, Any]]:
        all_feedback = self.store.load_feedback()
        categories: dict[str, dict[str, int]] = {}
        for fb in all_feedback:
            category = fb.rule_id.split("_")[0] if "_" in fb.rule_id else fb.rule_id
            if category not in categories:
                categories[category] = {"total": 0, "accepted": 0}
            categories[category]["total"] += 1
            if fb.feedback_type == "accept":
                categories[category]["accepted"] += 1
        result = {}
        for cat, data in categories.items():
            total = data["total"]
            result[cat] = {
                "total": total,
                "accepted": data["accepted"],
                "accuracy": round(data["accepted"] / total, 4) if total > 0 else 0.0,
            }
        return result

    def check_promotions(self) -> list[str]:
        promoted = []
        for rule in self.engine.rules:
            if rule.get("deployment") != "candidate":
                continue
            if rule.get("confidence", 0) >= self.promotion_threshold:
                rid = rule.get("id", "")
                self.engine.activate_rule(rid)
                promoted.append(rid)
                self.store.save_event(RuleEvent(
                    rule_id=rid, event_type="rule_promoted", direction="up",
                ))
                logger.info("Rule %s promoted to production", rid)
        return promoted
