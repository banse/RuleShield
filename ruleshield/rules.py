"""RuleShield Hermes -- Rule engine.

JSON-based pattern matching that intercepts LLM requests and returns
pre-computed responses, saving API costs for predictable prompts.

Enhanced with SAP enterprise patterns:
  - Weighted keyword + regex scoring (not just boolean matching).
  - Confidence levels (CONFIRMED/LIKELY/POSSIBLE) instead of simple float.
  - Dual-trigger matching: keyword AND context conditions scored together.
  - Minimum score threshold to prevent weak single-keyword false positives.
  - Score-based tie-breaking within the same priority tier.

Performance target: < 2ms per match call.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# SAP-inspired scoring weights
# ---------------------------------------------------------------------------
# These weights determine how different pattern types contribute to the
# overall match score.  Regex patterns are weighted higher because they
# express more specific intent than simple keyword containment.

KEYWORD_WEIGHT: float = 1.0    # contains / startswith matches
PATTERN_WEIGHT: float = 2.0    # regex matches (more specific)
EXACT_WEIGHT: float = 5.0      # exact string matches (highest specificity)
CONDITION_WEIGHT: float = 0.5  # satisfied conditions add a small bonus

# Default minimum score a rule must reach to be considered a match.
# Prevents weak single-keyword hits from firing prematurely.
DEFAULT_MIN_SCORE: float = 1.5  # Must have at least one real pattern match (not just conditions)

# ---------------------------------------------------------------------------
# Model-aware confidence thresholds
# ---------------------------------------------------------------------------
# Expensive models require higher confidence before a rule is applied.
# Cheap models are more tolerant -- a "risky" rule match is still cheaper
# than a full LLM call to an expensive model.
#
# Threshold = minimum rule confidence required for the match to fire.
# A rule with confidence 0.85 will fire for haiku (threshold 0.6)
# but NOT for opus (threshold 0.9).

MODEL_CONFIDENCE_THRESHOLDS: dict[str, float] = {
    # ── Cheap models (low threshold, rules fire aggressively) ────────────
    # OpenAI
    "gpt-4o-mini": 0.60,
    "gpt-4.1-mini": 0.60,
    "gpt-4.1-nano": 0.50,
    # Anthropic
    "claude-haiku": 0.60,
    "claude-haiku-4-5": 0.60,
    # Google
    "gemini-flash": 0.55,
    "gemini-2.0-flash": 0.55,
    "gemini-2.5-flash": 0.55,
    # DeepSeek
    "deepseek-chat": 0.55,
    "deepseek-v3": 0.55,
    "deepseek-r1-distill": 0.50,
    # Nous / Hermes (small)
    "hermes-4-14b": 0.55,
    "hermes-4.3-36b": 0.60,
    "hermes-3-llama-3.1-8b": 0.50,
    # Open Source (small)
    "llama-3.1-8b": 0.50,
    "llama-3.2-3b": 0.45,
    "llama-3.3-70b": 0.65,
    "qwen-2.5-7b": 0.50,
    "qwen-2.5-14b": 0.55,
    "qwen-2.5-32b": 0.60,
    "qwen-3-8b": 0.50,
    "qwen-3-32b": 0.60,
    "mistral-7b": 0.50,
    "mistral-small": 0.55,
    "phi-4": 0.55,
    "phi-4-mini": 0.50,
    "gemma-2-9b": 0.50,
    "gemma-2-27b": 0.60,
    "command-r": 0.60,
    # ── Mid-tier models (moderate threshold) ─────────────────────────────
    # OpenAI
    "gpt-4o": 0.75,
    "gpt-4.1": 0.75,
    "o4-mini": 0.75,
    # Anthropic
    "claude-sonnet": 0.75,
    "claude-sonnet-4-6": 0.75,
    # Google
    "gemini-pro": 0.75,
    "gemini-2.5-pro": 0.75,
    # DeepSeek
    "deepseek-r1": 0.75,
    # Nous / Hermes (large)
    "hermes-4-70b": 0.75,
    "hermes-3-llama-3.1-70b": 0.75,
    # Open Source (large)
    "llama-3.1-405b": 0.80,
    "qwen-2.5-72b": 0.75,
    "qwen-3-235b": 0.80,
    "mistral-large": 0.75,
    "mistral-medium": 0.70,
    "command-r-plus": 0.75,
    "dbrx": 0.70,
    "yi-large": 0.70,
    # OpenAI Codex
    "gpt-5.3-codex": 0.70,
    "gpt-5.2-codex": 0.70,
    "gpt-5.1-codex-mini": 0.60,
    "gpt-5.1-codex-max": 0.80,
    # ── Premium models (high threshold, only confident rules fire) ───────
    # OpenAI
    "gpt-4.5": 0.85,
    "o3": 0.90,
    "o1": 0.85,
    # Anthropic
    "claude-opus": 0.90,
    "claude-opus-4-6": 0.90,
    # Nous / Hermes (flagship)
    "hermes-4-405b": 0.85,
    "hermes-4-405b-fp8": 0.85,
    "hermes-4-70b-fp8": 0.75,
    "hermes-4-14b-fp8": 0.55,
    # ── Ollama / Local models (very cheap, aggressive rules) ──────────
    "llama3": 0.45,
    "llama3.1": 0.45,
    "llama3.2": 0.45,
    "llama3.3": 0.50,
    "mistral": 0.45,
    "mixtral": 0.55,
    "codellama": 0.50,
    "phi3": 0.45,
    "phi4": 0.50,
    "gemma2": 0.50,
    "qwen2.5": 0.50,
    "deepseek-coder": 0.50,
    "starcoder": 0.45,
    "yi": 0.50,
    "solar": 0.50,
    "command-r": 0.55,
    "nous-hermes": 0.50,
}

# Default threshold when model is unknown
DEFAULT_CONFIDENCE_THRESHOLD: float = 0.70


def _get_model_threshold(model: str) -> float:
    """Look up confidence threshold for a model.

    Tries exact match first, then partial match (model name contained in key
    or key contained in model name).  Falls back to DEFAULT_CONFIDENCE_THRESHOLD.
    """
    if not model:
        return DEFAULT_CONFIDENCE_THRESHOLD

    model_lower = model.lower()

    # Strip provider prefixes like "anthropic/claude-..." or "openai/gpt-..."
    if "/" in model_lower:
        model_lower = model_lower.rsplit("/", 1)[-1]

    # Handle Ollama format: "llama3:8b" -> "llama3"
    if ":" in model_lower:
        base_model = model_lower.split(":")[0]
        if base_model in MODEL_CONFIDENCE_THRESHOLDS:
            return MODEL_CONFIDENCE_THRESHOLDS[base_model]

    # Exact match
    if model_lower in MODEL_CONFIDENCE_THRESHOLDS:
        return MODEL_CONFIDENCE_THRESHOLDS[model_lower]

    # Partial match (e.g. "claude-4.6-sonnet-20260217" contains "claude-sonnet")
    for key, threshold in MODEL_CONFIDENCE_THRESHOLDS.items():
        if key in model_lower or model_lower.startswith(key.split("-")[0]):
            return threshold

    # Heuristic fallbacks based on keywords in model name
    # Premium tier
    if any(t in model_lower for t in ("opus", "o3", "o1", "405b", "codex-max")):
        return 0.90
    if "codex" in model_lower:
        return 0.70
    # Cheap tier
    if any(t in model_lower for t in (
        "haiku", "mini", "nano", "flash", "deepseek-chat",
        "8b", "7b", "3b", "1b", "phi-", "gemma",
        "distill", "tiny", "small",
    )):
        return 0.60
    # Mid tier
    if any(t in model_lower for t in (
        "sonnet", "4o", "4.1", "pro", "large", "plus",
        "70b", "72b", "36b", "32b", "mistral-large",
        "command-r", "hermes-4", "r1",
    )):
        return 0.75
    # Size-based heuristic: extract parameter count if present
    import re as _re
    size_match = _re.search(r"(\d+)[bB]", model_lower)
    if size_match:
        params_b = int(size_match.group(1))
        if params_b <= 14:
            return 0.55
        elif params_b <= 70:
            return 0.70
        else:
            return 0.80

    return DEFAULT_CONFIDENCE_THRESHOLD


# Pre-compile a small LRU for regex patterns to avoid recompilation.
_regex_cache: dict[str, re.Pattern] = {}


def _get_regex(pattern: str) -> re.Pattern:
    """Return a compiled regex, caching for reuse."""
    compiled = _regex_cache.get(pattern)
    if compiled is None:
        compiled = re.compile(pattern, re.IGNORECASE)
        # Cap cache size to prevent unbounded growth.
        if len(_regex_cache) > 1024:
            _regex_cache.clear()
        _regex_cache[pattern] = compiled
    return compiled


def _extract_last_user_message(messages: list[dict[str, Any]] | None) -> str:
    """Pull the last user message content from an OpenAI-style messages list.

    Handles both plain-string content and multi-part content arrays.
    Returns an empty string when no user message is found.
    """
    if not messages:
        return ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                # Multi-part content -- concatenate text parts.
                parts = [
                    p["text"]
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                return " ".join(parts).strip()
    return ""


class RuleEngine:
    """Matches incoming prompts against cost-saving rules.

    Rules are loaded from JSON files in a configurable directory.  On first
    init the engine copies bundled default rules into the user directory if it
    is empty, providing a useful out-of-the-box experience.

    Match semantics:
      - Patterns are evaluated with OR logic (any match fires the rule).
      - Conditions are evaluated with AND logic (all must be satisfied).
      - Rules are tried in descending priority order; first match wins.
      - Each successful match increments the rule's ``hit_count``.
      - Rules with confidence below ``deactivation_threshold`` are skipped.
    """

    def __init__(
        self,
        rules_dir: str = "~/.ruleshield/rules/",
        min_score_threshold: float = DEFAULT_MIN_SCORE,
    ):
        self.rules: list[dict[str, Any]] = []
        self.rules_dir: str = os.path.expanduser(rules_dir)
        self._loaded = False
        self.deactivation_threshold: float = 0.5
        self._dirty = False  # True when in-memory state diverges from disk
        self._match_count_since_save = 0
        self._save_interval = 100  # persist to disk every N matches
        self.min_score_threshold: float = min_score_threshold

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self, rules_dir: str = "") -> None:
        """Load rules from JSON files.

        If *rules_dir* is provided it overrides the constructor default.
        If the target directory is empty or missing, the bundled default
        rules file is copied there automatically.
        """
        if rules_dir:
            self.rules_dir = os.path.expanduser(rules_dir)

        os.makedirs(self.rules_dir, exist_ok=True)

        # Copy defaults when the directory has no JSON files.
        json_files = [
            fp for fp in Path(self.rules_dir).glob("*.json")
            if fp.name != "_state.json"
        ]
        if not json_files:
            self._copy_defaults()
            json_files = [
                fp for fp in Path(self.rules_dir).glob("*.json")
                if fp.name != "_state.json"
            ]

        # Also load promoted rules from the promoted/ subdirectory.
        promoted_dir = Path(self.rules_dir) / "promoted"
        if promoted_dir.is_dir():
            json_files.extend(promoted_dir.glob("*.json"))

        # Load candidate rules from the candidates/ subdirectory.
        # These are disabled by default and participate in shadow mode only.
        candidates_dir = Path(self.rules_dir) / "candidates"
        if candidates_dir.is_dir():
            json_files.extend(candidates_dir.glob("*.json"))

        await self._load_rules(json_files)
        self._loaded = True

    async def reload(self) -> int:
        """Reload rules from disk.  Returns the number of rules loaded."""
        json_files = [
            fp for fp in Path(self.rules_dir).glob("*.json")
            if fp.name != "_state.json"
        ]
        # Also reload promoted rules from the promoted/ subdirectory.
        promoted_dir = Path(self.rules_dir) / "promoted"
        if promoted_dir.is_dir():
            json_files.extend(promoted_dir.glob("*.json"))
        # Also reload candidate rules from the candidates/ subdirectory.
        candidates_dir = Path(self.rules_dir) / "candidates"
        if candidates_dir.is_dir():
            json_files.extend(candidates_dir.glob("*.json"))
        await self._load_rules(json_files)
        return len(self.rules)

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def match(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        model: str = "",
        confidence_floor: float | None = None,
    ) -> dict[str, Any] | None:
        """Match only production rules.

        Candidate rules are evaluated separately via :meth:`match_candidates`
        so shadow-mode learning does not accidentally leak into live replies.
        """
        return self._match_with_scope(
            prompt_text,
            messages=messages,
            model=model,
            deployment="production",
            hit_field="hit_count",
            confidence_floor=confidence_floor,
        )

    def match_candidates(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        model: str = "",
        confidence_floor: float | None = None,
    ) -> dict[str, Any] | None:
        """Match shadow-only candidate rules without affecting live hit counts."""
        return self._match_with_scope(
            prompt_text,
            messages=messages,
            model=model,
            deployment="candidate",
            hit_field="shadow_hit_count",
            confidence_floor=confidence_floor,
        )

    def _match_with_scope(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        model: str = "",
        *,
        deployment: str,
        hit_field: str,
        confidence_floor: float | None = None,
    ) -> dict[str, Any] | None:
        """Match *prompt_text* (and optional *messages*) against loaded rules.

        Uses weighted scoring (SAP enterprise pattern) to rank matches:
          - Each pattern type contributes a different weight to the score.
          - A minimum score threshold prevents weak single-keyword matches.
          - Within the same priority tier, the highest-scoring rule wins.

        Model-aware confidence thresholds:
          - Expensive models (Opus, O3) require high confidence (0.90) to fire.
          - Mid-tier models (Sonnet, GPT-4o) require moderate confidence (0.75).
          - Cheap models (Haiku, mini) accept lower confidence (0.60).
          - This ensures risky rules only fire when savings justify the risk.

        Returns a dict on match::

            {
                "response": {"content": "...", "model": "ruleshield-rule"},
                "rule_id": "greeting_simple",
                "rule_name": "Simple Greeting",
                "confidence": 0.95,
                "match_score": 3.0,
                "confidence_level": "LIKELY",
                "matched_keywords": ["hello"],
                "matched_patterns": ["^hi\\\\b"],
                "model_threshold": 0.75,
            }

        Returns ``None`` when no rule fires.
        """
        last_user_msg = _extract_last_user_message(messages) or prompt_text
        msg_count = len(messages) if messages else 0

        # Model-aware threshold: expensive models require higher confidence.
        model_threshold = _get_model_threshold(model)

        # Collect all eligible rule scores so we can pick the best match
        # within each priority tier.  Rules are already sorted by priority
        # descending, so we iterate in order and track the best candidate
        # within the current (highest) priority group.
        best: dict[str, Any] | None = None
        best_score: float = 0.0
        best_priority: int | None = None

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue
            if rule.get("deployment", "production") != deployment:
                continue

            # Skip rules whose confidence has fallen below the deactivation floor.
            rule_confidence = float(rule.get("confidence", 1.0))
            effective_confidence = rule_confidence
            if confidence_floor is not None:
                effective_confidence = max(effective_confidence, float(confidence_floor))
            if rule_confidence < self.deactivation_threshold:
                continue

            # Model-aware check: skip rules whose confidence is below the
            # threshold for the current model.  A rule with 0.85 confidence
            # fires for haiku (threshold 0.60) but not for opus (0.90).
            if effective_confidence < model_threshold:
                continue

            # If we already have a candidate and this rule is in a lower
            # priority tier, stop -- the best match is finalised.
            rule_priority = rule.get("priority", 0)
            if best is not None and rule_priority < best_priority:
                break

            if not self._conditions_met(rule, last_user_msg, msg_count):
                continue

            score, matched_kw, matched_pat = self._score_rule(rule, last_user_msg)

            # Conditions only add bonus if a real pattern matched (SAP dual-trigger).
            # Without this guard, conditions alone (max_length etc.) would cause
            # false positives on any short prompt.
            if score > 0:
                conditions = rule.get("conditions", [])
                if conditions:
                    score += len(conditions) * CONDITION_WEIGHT

            # Skip rules below the minimum score threshold.
            if score < self.min_score_threshold:
                continue

            if score > best_score:
                has_keywords = len(matched_kw) > 0
                has_patterns = len(matched_pat) > 0
                confidence_level = self._compute_confidence_level(
                    score, has_keywords, has_patterns,
                )
                best_score = score
                best_priority = rule_priority
                best = {
                    "response": rule["response"],
                    "rule_id": rule["id"],
                    "rule_name": rule.get("name", rule["id"]),
                    "deployment": rule.get("deployment", "production"),
                    "confidence": rule.get("confidence", 1.0),
                    "match_score": score,
                    "confidence_level": confidence_level,
                    "matched_keywords": matched_kw,
                    "matched_patterns": matched_pat,
                    "model_threshold": model_threshold,
                    "_rule_ref": rule,  # internal: used for bookkeeping below
                }

        if best is None:
            return None

        # Track the winning rule in the relevant counter without mixing
        # production hits and shadow candidate evaluations.
        winning_rule = best.pop("_rule_ref")
        winning_rule[hit_field] = winning_rule.get(hit_field, 0) + 1
        self._dirty = True
        self._match_count_since_save += 1

        # Periodically persist updated hit counts / confidence to disk.
        if self._match_count_since_save >= self._save_interval:
            self._save_rules_to_disk()

        return best

    # Backward-compatible async wrapper used by proxy.py stub signature.
    async def async_match(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        model: str = "",
        confidence_floor: float | None = None,
    ) -> dict[str, Any] | None:
        """Async wrapper around :meth:`match` for callers that expect a coroutine."""
        return self.match(
            prompt_text,
            messages,
            model=model,
            confidence_floor=confidence_floor,
        )

    async def async_match_candidates(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        model: str = "",
        confidence_floor: float | None = None,
    ) -> dict[str, Any] | None:
        """Async wrapper around :meth:`match_candidates`."""
        return self.match_candidates(
            prompt_text,
            messages,
            model=model,
            confidence_floor=confidence_floor,
        )

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def get_active_rules(self) -> list[dict[str, Any]]:
        """Return all active rules with hit counts."""
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
            }
            for r in self.rules
            if r.get("enabled", True)
        ]

    async def list_rules(self) -> list[dict[str, Any]]:
        """Return all loaded rules as a list of dicts (proxy compat)."""
        return self.get_active_rules()

    def add_rule(self, rule: dict[str, Any]) -> None:
        """Add a new rule dynamically and re-sort by priority."""
        rule.setdefault("enabled", True)
        rule.setdefault("hit_count", 0)
        rule.setdefault("shadow_hit_count", 0)
        rule.setdefault("confidence", 0.9)
        rule.setdefault("priority", 0)
        rule.setdefault("deployment", "production")
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.get("priority", 0), reverse=True)

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate rule statistics.

        Returns::

            {
                "total_rules": 8,
                "active_rules": 8,
                "total_hits": 42,
                "top_rules": [{"id": "...", "name": "...", "hit_count": 10}, ...],
            }
        """
        active = [r for r in self.rules if r.get("enabled", True)]
        total_hits = sum(r.get("hit_count", 0) for r in self.rules)
        top = sorted(self.rules, key=lambda r: r.get("hit_count", 0), reverse=True)[:5]
        return {
            "total_rules": len(self.rules),
            "active_rules": len(active),
            "total_hits": total_hits,
            "top_rules": [
                {
                    "id": r["id"],
                    "name": r.get("name", r["id"]),
                    "hit_count": r.get("hit_count", 0),
                    "shadow_hit_count": r.get("shadow_hit_count", 0),
                }
                for r in top
            ],
        }

    # ------------------------------------------------------------------
    # Feedback integration
    # ------------------------------------------------------------------

    def update_confidence(self, rule_id: str, new_confidence: float) -> bool:
        """Update the confidence score for a rule identified by *rule_id*.

        Returns True if the rule was found and updated, False otherwise.
        """
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["confidence"] = max(0.0, min(1.0, new_confidence))
                self._dirty = True
                return True
        return False

    def deactivate_rule(self, rule_id: str) -> bool:
        """Disable a rule by setting ``enabled`` to False.

        This is typically called by the feedback loop when a rule's
        confidence drops below the deactivation threshold.

        Returns True if the rule was found and deactivated, False otherwise.
        """
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = False
                self._dirty = True
                return True
        return False

    def activate_rule(self, rule_id: str) -> bool:
        """Activate a previously disabled rule.

        This is typically called by the auto-promotion system when a
        candidate rule has proven itself through shadow mode comparisons
        and positive feedback.

        Returns True if the rule was found and activated, False otherwise.
        """
        for rule in self.rules:
            if rule.get("id") == rule_id:
                rule["enabled"] = True
                rule["deployment"] = "production"
                self._dirty = True
                self._save_rules_to_disk()
                return True
        return False

    def _save_rules_to_disk(self) -> None:
        """Persist the current in-memory rule state back to JSON files.

        Groups rules by their source file (if tracked) or writes all rules
        to a single ``_state.json`` file that captures runtime changes such
        as updated hit_count and confidence values.
        """
        if not self._dirty:
            return

        state_path = Path(self.rules_dir) / "_state.json"
        serialisable = []
        for rule in self.rules:
            # Write a lightweight copy with the fields that change at runtime.
            serialisable.append({
                "id": rule.get("id"),
                "hit_count": rule.get("hit_count", 0),
                "shadow_hit_count": rule.get("shadow_hit_count", 0),
                "confidence": rule.get("confidence", 1.0),
                "enabled": rule.get("enabled", True),
                "deployment": rule.get("deployment", "production"),
            })

        try:
            with open(state_path, "w", encoding="utf-8") as fh:
                json.dump(serialisable, fh, indent=2)
            self._dirty = False
            self._match_count_since_save = 0
        except OSError:
            pass  # Best effort -- do not crash on write failure.

    def _apply_persisted_state(self) -> None:
        """Merge runtime state from ``_state.json`` into loaded rules."""
        state_path = Path(self.rules_dir) / "_state.json"
        if not state_path.is_file():
            return

        try:
            with open(state_path, "r", encoding="utf-8") as fh:
                state_entries = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return

        state_map: dict[str, dict[str, Any]] = {}
        for entry in state_entries:
            rid = entry.get("id")
            if rid:
                state_map[rid] = entry

        for rule in self.rules:
            rid = rule.get("id")
            if rid and rid in state_map:
                saved = state_map[rid]
                rule["hit_count"] = saved.get("hit_count", rule.get("hit_count", 0))
                rule["shadow_hit_count"] = saved.get(
                    "shadow_hit_count", rule.get("shadow_hit_count", 0)
                )
                rule["confidence"] = saved.get("confidence", rule.get("confidence", 1.0))
                rule["enabled"] = saved.get("enabled", rule.get("enabled", True))
                rule["deployment"] = saved.get(
                    "deployment", rule.get("deployment", "production")
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _copy_defaults(self) -> None:
        """Copy all bundled rule JSON files into the user rules dir."""
        bundled_dir = Path(__file__).resolve().parent.parent / "rules"
        if not bundled_dir.is_dir():
            return
        for bundled in bundled_dir.glob("*.json"):
            dest = Path(self.rules_dir) / bundled.name
            if not dest.exists():
                shutil.copy2(str(bundled), str(dest))

    async def _load_rules(self, json_files: list[Path]) -> None:
        """Parse all JSON rule files and sort by descending priority."""
        rules: list[dict[str, Any]] = []
        for fp in json_files:
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                loaded = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
                deployment = "candidate" if fp.parent.name == "candidates" else "production"
                for rule in loaded:
                    # Ignore runtime-state objects accidentally placed in JSON files.
                    # Real rules must define at least patterns and response payload.
                    if not isinstance(rule, dict):
                        continue
                    if "patterns" not in rule or "response" not in rule:
                        continue
                    rule.setdefault("deployment", deployment)
                    rule.setdefault("shadow_hit_count", 0)
                    rules.append(rule)
            except (json.JSONDecodeError, OSError):
                # Skip malformed files silently during init.
                continue

        # Sort by priority descending so highest-priority rules match first.
        rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
        self.rules = rules

        # Merge any persisted runtime state (hit counts, confidence, enabled).
        self._apply_persisted_state()

    # ---- scoring (SAP enterprise pattern) ----

    def _score_rule(
        self,
        rule: dict,
        prompt_text: str,
    ) -> tuple[float, list[str], list[str]]:
        """Score a rule match with weighted keywords + patterns.

        Inspired by SAP enterprise rule engines that assign different weights
        to different match types instead of treating all pattern hits equally.

        Returns:
            (score, matched_keywords, matched_patterns) where
            matched_keywords lists values of contains/startswith hits and
            matched_patterns lists values of regex/exact hits.
        """
        score = 0.0
        matched_keywords: list[str] = []
        matched_patterns: list[str] = []

        text = prompt_text  # may be overridden per-pattern via field

        for pat in rule.get("patterns", []):
            ptype = pat.get("type", "contains")
            value = pat.get("value", "")
            field_text = self._resolve_field(
                pat.get("field", "last_user_message"), text,
            )

            if ptype in ("contains", "startswith"):
                if self._single_pattern_matches(ptype, value, field_text):
                    score += KEYWORD_WEIGHT
                    matched_keywords.append(value)

            elif ptype == "regex":
                try:
                    if _get_regex(value).search(field_text):
                        score += PATTERN_WEIGHT
                        matched_patterns.append(value)
                except re.error:
                    pass

            elif ptype == "exact":
                if value.lower() == field_text.lower():
                    score += EXACT_WEIGHT
                    matched_patterns.append(value)

        return score, matched_keywords, matched_patterns

    @staticmethod
    def _compute_confidence_level(
        score: float,
        has_keywords: bool,
        has_patterns: bool,
    ) -> str:
        """Compute a discrete confidence level from the numeric score.

        SAP enterprise pattern: instead of exposing raw floats to callers,
        bucket the score into human-readable tiers that drive downstream
        behaviour (e.g. auto-respond for CONFIRMED, shadow-verify for
        LIKELY, log-only for POSSIBLE).

        Thresholds:
          - CONFIRMED: score >= 4.0 AND both keyword and pattern hits
          - LIKELY:    score >= 2.0
          - POSSIBLE:  score > 0
          - NONE:      no match
        """
        if score >= 4.0 and has_keywords and has_patterns:
            return "CONFIRMED"
        if score >= 2.0:
            return "LIKELY"
        if score > 0:
            return "POSSIBLE"
        return "NONE"

    # ---- pattern matching ----

    @staticmethod
    def _resolve_field(rule_field: str, last_user_msg: str) -> str:
        """Resolve a pattern/condition field name to the actual text value."""
        # Currently the only supported field is last_user_message.
        # Extensible for future field types.
        return last_user_msg

    def _patterns_match(self, rule: dict, last_user_msg: str) -> bool:
        """Return True if ANY pattern in the rule matches (OR logic)."""
        patterns = rule.get("patterns", [])
        if not patterns:
            return False

        for pat in patterns:
            ptype = pat.get("type", "contains")
            value = pat.get("value", "")
            text = self._resolve_field(pat.get("field", "last_user_message"), last_user_msg)

            if self._single_pattern_matches(ptype, value, text):
                return True
        return False

    @staticmethod
    def _single_pattern_matches(ptype: str, value: str, text: str) -> bool:
        """Evaluate a single pattern against *text*."""
        text_lower = text.lower()
        value_lower = value.lower()

        if ptype == "contains":
            return value_lower in text_lower
        if ptype == "startswith":
            return text_lower.startswith(value_lower)
        if ptype == "exact":
            return text_lower == value_lower
        if ptype == "regex":
            try:
                return bool(_get_regex(value).search(text))
            except re.error:
                return False
        return False

    def _conditions_met(
        self,
        rule: dict,
        last_user_msg: str,
        msg_count: int,
    ) -> bool:
        """Return True if ALL conditions in the rule are satisfied (AND logic)."""
        conditions = rule.get("conditions", [])
        for cond in conditions:
            ctype = cond.get("type", "")
            cvalue = cond.get("value", 0)
            text = self._resolve_field(cond.get("field", "last_user_message"), last_user_msg)

            if ctype == "max_length" and len(text) > cvalue:
                return False
            if ctype == "min_length" and len(text) < cvalue:
                return False
            if ctype == "max_messages" and msg_count > cvalue:
                return False
        return True
