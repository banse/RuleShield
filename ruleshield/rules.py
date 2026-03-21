"""RuleShield Hermes -- Rule engine adapter.

Thin wrapper around rulecore.RuleEngine that adds LLM-specific
model-aware confidence thresholds, OpenAI message format handling,
and async compatibility. Preserves the exact same public API.

Performance target: < 2ms per match call.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from rulecore.engine import RuleEngine as _CoreEngine
from rulecore.types import ScoringConfig

# ---------------------------------------------------------------------------
# Re-export weight constants for backward compatibility
# ---------------------------------------------------------------------------

KEYWORD_WEIGHT: float = 1.0
PATTERN_WEIGHT: float = 2.0
EXACT_WEIGHT: float = 5.0
CONDITION_WEIGHT: float = 0.5
DEFAULT_MIN_SCORE: float = 1.5

# ---------------------------------------------------------------------------
# Model-aware confidence thresholds (LLM-specific, not in rulecore)
# ---------------------------------------------------------------------------

MODEL_CONFIDENCE_THRESHOLDS: dict[str, float] = {
    # ── Cheap models ────────────────────────────────────────────────
    "gpt-4o-mini": 0.60, "gpt-4.1-mini": 0.60, "gpt-4.1-nano": 0.50,
    "claude-haiku": 0.60, "claude-haiku-4-5": 0.60,
    "gemini-flash": 0.55, "gemini-2.0-flash": 0.55, "gemini-2.5-flash": 0.55,
    "deepseek-chat": 0.55, "deepseek-v3": 0.55, "deepseek-r1-distill": 0.50,
    "hermes-4-14b": 0.55, "hermes-4.3-36b": 0.60, "hermes-3-llama-3.1-8b": 0.50,
    "llama-3.1-8b": 0.50, "llama-3.2-3b": 0.45, "llama-3.3-70b": 0.65,
    "qwen-2.5-7b": 0.50, "qwen-2.5-14b": 0.55, "qwen-2.5-32b": 0.60,
    "qwen-3-8b": 0.50, "qwen-3-32b": 0.60,
    "mistral-7b": 0.50, "mistral-small": 0.55,
    "phi-4": 0.55, "phi-4-mini": 0.50,
    "gemma-2-9b": 0.50, "gemma-2-27b": 0.60, "command-r": 0.60,
    # ── Mid-tier models ─────────────────────────────────────────────
    "gpt-4o": 0.75, "gpt-4.1": 0.75, "o4-mini": 0.75,
    "claude-sonnet": 0.75, "claude-sonnet-4-6": 0.75,
    "gemini-pro": 0.75, "gemini-2.5-pro": 0.75,
    "deepseek-r1": 0.75,
    "hermes-4-70b": 0.75, "hermes-3-llama-3.1-70b": 0.75,
    "llama-3.1-405b": 0.80, "qwen-2.5-72b": 0.75, "qwen-3-235b": 0.80,
    "mistral-large": 0.75, "mistral-medium": 0.70,
    "command-r-plus": 0.75, "dbrx": 0.70, "yi-large": 0.70,
    "gpt-5.3-codex": 0.70, "gpt-5.2-codex": 0.70,
    "gpt-5.1-codex-mini": 0.60, "gpt-5.1-codex-max": 0.80,
    # ── Premium models ──────────────────────────────────────────────
    "gpt-4.5": 0.85, "o3": 0.90, "o1": 0.85,
    "claude-opus": 0.90, "claude-opus-4-6": 0.90,
    "hermes-4-405b": 0.85, "hermes-4-405b-fp8": 0.85,
    "hermes-4-70b-fp8": 0.75, "hermes-4-14b-fp8": 0.55,
    # ── Ollama / Local models ───────────────────────────────────────
    "llama3": 0.45, "llama3.1": 0.45, "llama3.2": 0.45, "llama3.3": 0.50,
    "mistral": 0.45, "mixtral": 0.55, "codellama": 0.50,
    "phi3": 0.45, "phi4": 0.50, "gemma2": 0.50, "qwen2.5": 0.50,
    "deepseek-coder": 0.50, "starcoder": 0.45, "yi": 0.50, "solar": 0.50,
    "command-r": 0.55, "nous-hermes": 0.50,
}

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.70


def _get_model_threshold(model: str) -> float:
    """Look up confidence threshold for a model."""
    if not model:
        return DEFAULT_CONFIDENCE_THRESHOLD

    model_lower = model.lower()

    if "/" in model_lower:
        model_lower = model_lower.rsplit("/", 1)[-1]

    if ":" in model_lower:
        base_model = model_lower.split(":")[0]
        if base_model in MODEL_CONFIDENCE_THRESHOLDS:
            return MODEL_CONFIDENCE_THRESHOLDS[base_model]

    if model_lower in MODEL_CONFIDENCE_THRESHOLDS:
        return MODEL_CONFIDENCE_THRESHOLDS[model_lower]

    for key, threshold in MODEL_CONFIDENCE_THRESHOLDS.items():
        if key in model_lower or model_lower.startswith(key.split("-")[0]):
            return threshold

    if any(t in model_lower for t in ("opus", "o3", "o1", "405b", "codex-max")):
        return 0.90
    if "codex" in model_lower:
        return 0.70
    if any(t in model_lower for t in (
        "haiku", "mini", "nano", "flash", "deepseek-chat",
        "8b", "7b", "3b", "1b", "phi-", "gemma", "distill", "tiny", "small",
    )):
        return 0.60
    if any(t in model_lower for t in (
        "sonnet", "4o", "4.1", "pro", "large", "plus",
        "70b", "72b", "36b", "32b", "mistral-large",
        "command-r", "hermes-4", "r1",
    )):
        return 0.75

    size_match = re.search(r"(\d+)[bB]", model_lower)
    if size_match:
        params_b = int(size_match.group(1))
        if params_b <= 14:
            return 0.55
        elif params_b <= 70:
            return 0.70
        else:
            return 0.80

    return DEFAULT_CONFIDENCE_THRESHOLD


def _extract_last_user_message(messages: list[dict[str, Any]] | None) -> str:
    """Pull the last user message content from an OpenAI-style messages list."""
    if not messages:
        return ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts = [
                    p["text"]
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                return " ".join(parts).strip()
    return ""


def _inject_default_field(rules: list[dict[str, Any]]) -> None:
    """Inject 'field': 'last_user_message' into patterns/conditions that lack it."""
    for rule in rules:
        for pat in rule.get("patterns", []):
            pat.setdefault("field", "last_user_message")
        for cond in rule.get("conditions", []):
            cond.setdefault("field", "last_user_message")


class RuleEngine:
    """RuleShield rule engine — adapter around rulecore.RuleEngine.

    Adds LLM-specific model-aware confidence thresholds, OpenAI message
    format handling, and async compatibility.
    """

    def __init__(
        self,
        rules_dir: str = "~/.ruleshield/rules/",
        min_score_threshold: float = DEFAULT_MIN_SCORE,
    ):
        self.rules_dir: str = os.path.expanduser(rules_dir)
        self.min_score_threshold: float = min_score_threshold
        self.deactivation_threshold: float = 0.5
        self._core = _CoreEngine(
            rules_dir=self.rules_dir,
            scoring=ScoringConfig(min_score=min_score_threshold),
        )
        self._loaded = False

    @property
    def rules(self) -> list[dict[str, Any]]:
        return self._core.rules

    @rules.setter
    def rules(self, value: list[dict[str, Any]]) -> None:
        self._core.rules = value

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init(self, rules_dir: str = "") -> None:
        if rules_dir:
            self.rules_dir = os.path.expanduser(rules_dir)
            self._core.rules_dir = self.rules_dir

        bundled_dir = str(Path(__file__).resolve().parent.parent / "rules")
        self._core.bundled_dir = bundled_dir

        self._core.load()
        _inject_default_field(self._core.rules)
        self._core.deactivation_threshold = self.deactivation_threshold
        self._loaded = True

    async def reload(self) -> int:
        self._core.load()
        _inject_default_field(self._core.rules)
        return len(self._core.rules)

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
        return self._match_with_scope(
            prompt_text, messages=messages, model=model,
            deployment="production", hit_field="hit_count",
            confidence_floor=confidence_floor,
        )

    def match_candidates(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        model: str = "",
        confidence_floor: float | None = None,
    ) -> dict[str, Any] | None:
        return self._match_with_scope(
            prompt_text, messages=messages, model=model,
            deployment="candidate", hit_field="shadow_hit_count",
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
        last_user_msg = _extract_last_user_message(messages) or prompt_text
        msg_count = len(messages) if messages else 0

        model_threshold = _get_model_threshold(model)
        effective_threshold = model_threshold
        if confidence_floor is not None:
            effective_threshold = max(effective_threshold, float(confidence_floor))

        context = {"last_user_message": last_user_msg, "msg_count": msg_count}

        if deployment == "candidate":
            result = self._core.match_candidates(
                context=context,
                confidence_threshold=effective_threshold,
            )
        else:
            result = self._core.match(
                context=context,
                confidence_threshold=effective_threshold,
            )

        if result is None:
            return None

        return {
            "response": result.response,
            "rule_id": result.rule_id,
            "rule_name": result.rule_name,
            "deployment": result.deployment,
            "confidence": result.confidence,
            "match_score": result.match_score,
            "confidence_level": result.confidence_level,
            "matched_keywords": result.matched_keywords,
            "matched_patterns": result.matched_patterns,
            "model_threshold": model_threshold,
        }

    async def async_match(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        model: str = "",
        confidence_floor: float | None = None,
    ) -> dict[str, Any] | None:
        return self.match(prompt_text, messages, model=model, confidence_floor=confidence_floor)

    async def async_match_candidates(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        model: str = "",
        confidence_floor: float | None = None,
    ) -> dict[str, Any] | None:
        return self.match_candidates(prompt_text, messages, model=model, confidence_floor=confidence_floor)

    # ------------------------------------------------------------------
    # Rule management (delegate to core)
    # ------------------------------------------------------------------

    def get_active_rules(self) -> list[dict[str, Any]]:
        return self._core.get_active_rules()

    async def list_rules(self) -> list[dict[str, Any]]:
        return self.get_active_rules()

    def add_rule(self, rule: dict[str, Any]) -> None:
        self._core.add_rule(rule)

    def get_stats(self) -> dict[str, Any]:
        return self._core.get_stats()

    def update_confidence(self, rule_id: str, new_confidence: float) -> bool:
        return self._core.update_confidence(rule_id, new_confidence)

    def deactivate_rule(self, rule_id: str) -> bool:
        return self._core.deactivate_rule(rule_id)

    def activate_rule(self, rule_id: str) -> bool:
        return self._core.activate_rule(rule_id)

    def _save_rules_to_disk(self) -> None:
        from rulecore.loader import save_state
        save_state(self._core.rules, self.rules_dir)
        self._core._dirty = False
        self._core._match_count_since_save = 0

    @property
    def _dirty(self) -> bool:
        return self._core._dirty

    @_dirty.setter
    def _dirty(self, value: bool) -> None:
        self._core._dirty = value
