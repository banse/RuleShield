"""RuleShield Hermes -- Smart Model Router (Layer 3).

Routes requests to cost-appropriate models based on complexity heuristics.
Simple prompts go to cheap models, complex ones stay on premium models.

Classification is pure heuristic -- no ML, no network calls, sub-1ms latency.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

logger = logging.getLogger("ruleshield.router")

# ---------------------------------------------------------------------------
# Keyword sets for complexity detection
# ---------------------------------------------------------------------------

_CODE_KEYWORDS = frozenset({
    "code", "debug", "fix", "implement", "function", "class", "error",
    "traceback", "stacktrace", "refactor", "compile", "syntax", "bug",
    "algorithm", "api", "endpoint", "database", "query", "schema",
    "deploy", "dockerfile", "kubernetes", "terraform", "pipeline",
})

_ANALYSIS_KEYWORDS = frozenset({
    "analyze", "analyse", "compare", "evaluate", "review", "explain",
    "summarize", "summarise", "critique", "assess", "investigate",
    "research", "design", "architect", "plan", "strategy", "tradeoff",
    "trade-off", "pros and cons", "advantages", "disadvantages",
})

_SIMPLE_PATTERNS = re.compile(
    r"^(yes|no|ok|okay|sure|thanks|thank you|hi|hello|hey|"
    r"what is|who is|when is|where is|how old|"
    r"translate .{1,30}|define \w+|"
    r"what does \w+ mean|"
    r"is .{1,40}\?)\s*$",
    re.IGNORECASE,
)

_MULTISTEP_MARKERS = re.compile(
    r"\b(first|then|next|finally|step\s*\d|additionally|furthermore|"
    r"after that|followed by|in addition|moreover|"
    r"1\.|2\.|3\.|\ba\)|\bb\)|\bc\))\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# ComplexityClassifier
# ---------------------------------------------------------------------------


class ComplexityClassifier:
    """Scores request complexity from 1-10 based on fast heuristics.

    Design goals:
    - Sub-1ms execution time (pure string operations, no I/O)
    - Deterministic output for the same input
    - Conservative: when in doubt, score higher (avoid under-routing)
    """

    def score(self, prompt_text: str, messages: list[dict] | None = None) -> int:
        """Return complexity score 1-10.

        Combines length-based baseline with keyword and structure adjustments.
        """
        if not prompt_text:
            return 1

        text_lower = prompt_text.lower().strip()
        words = text_lower.split()
        char_len = len(text_lower)

        # --- Baseline: length-based score ----------------------------------
        if char_len < 20:
            base = 1
        elif char_len < 50:
            base = 3
        elif char_len < 100:
            base = 4
        elif char_len < 200:
            base = 6
        elif char_len < 500:
            base = 7
        elif char_len < 1000:
            base = 8
        else:
            base = 9

        adjustment = 0

        # --- Adjust UP for complex indicators ------------------------------

        # Code-related keywords (+1 per keyword, max +3)
        code_hits = sum(1 for w in words if w in _CODE_KEYWORDS)
        adjustment += min(code_hits, 3)

        # Analysis keywords (+1 per keyword, max +2)
        analysis_hits = sum(1 for w in words if w in _ANALYSIS_KEYWORDS)
        adjustment += min(analysis_hits, 2)

        # Multi-step indicators (+2 if multiple found)
        multistep_matches = _MULTISTEP_MARKERS.findall(text_lower)
        if len(multistep_matches) >= 2:
            adjustment += 2
        elif len(multistep_matches) == 1:
            adjustment += 1

        # Conversation depth: more messages = more complex context
        if messages:
            msg_count = len(messages)
            if msg_count > 10:
                adjustment += 2
            elif msg_count > 4:
                adjustment += 1

        # --- Adjust DOWN for simple indicators -----------------------------

        # Simple/short questions and greetings
        if _SIMPLE_PATTERNS.match(text_lower):
            adjustment -= 3

        # Very short single-sentence without complex markers
        if char_len < 30 and "?" in text_lower and code_hits == 0:
            adjustment -= 1

        # --- Clamp to 1-10 ------------------------------------------------
        final = max(1, min(10, base + adjustment))
        return final


# ---------------------------------------------------------------------------
# SmartRouter
# ---------------------------------------------------------------------------


class SmartRouter:
    """Routes requests to appropriate models based on complexity.

    The router sits between the rule engine and the upstream LLM call.
    If the request is simple enough, it swaps the target model for a
    cheaper alternative -- saving cost without meaningfully degrading
    quality for trivial prompts.
    """

    def __init__(self, config: dict | None = None) -> None:
        self.classifier = ComplexityClassifier()

        self.routes = config.get("routes") if config and "routes" in config else {
            "low": {"max_score": 3, "model": None, "label": "cheap"},
            "medium": {"max_score": 6, "model": None, "label": "mid"},
            "high": {"max_score": 10, "model": None, "label": "premium"},
        }

        # Model mappings: provider key -> {cheap, mid, premium}
        self.model_map: dict[str, dict[str, str | None]] = {
            "nousresearch": {
                "cheap": "deepseek/deepseek-chat-v3-0324",
                "mid": "claude-haiku-4-5",
                "premium": None,  # keep original
            },
            "openai": {
                "cheap": "gpt-4o-mini",
                "mid": "gpt-4o",
                "premium": None,
            },
            "anthropic": {
                "cheap": "claude-haiku-4-5",
                "mid": "claude-sonnet-4-6",
                "premium": None,
            },
            "google": {
                "cheap": "gemini-2.0-flash",
                "mid": "gemini-2.5-pro",
                "premium": None,
            },
            "openrouter": {
                "cheap": "deepseek/deepseek-chat-v3-0324",
                "mid": "anthropic/claude-haiku-4-5",
                "premium": None,
            },
            "deepseek": {
                "cheap": "deepseek-chat",
                "mid": "deepseek-reasoner",
                "premium": None,
            },
            "mistral": {
                "cheap": "mistral-small-latest",
                "mid": "mistral-large-latest",
                "premium": None,
            },
            "ollama": {
                "cheap": None,   # keep original (already local/free)
                "mid": None,
                "premium": None,  # no routing for local models
            },
            "default": {
                "cheap": "claude-haiku-4-5",
                "mid": "claude-sonnet-4-6",
                "premium": None,
            },
        }

        # Allow config to override model maps
        if config and "model_map" in config:
            self.model_map.update(config["model_map"])

        # --- Stats tracking (thread-safe) ----------------------------------
        self._lock = threading.Lock()
        self._stats: dict[str, int] = {"cheap": 0, "mid": 0, "premium": 0}
        self._total_routed = 0
        self._total_requests = 0

    # -- Public API ---------------------------------------------------------

    def route(
        self,
        prompt_text: str,
        messages: list[dict] | None,
        original_model: str,
        provider_url: str = "",
    ) -> dict[str, Any]:
        """Decide which model to use based on complexity scoring.

        Returns a dict with:
            model:            replacement model name, or None (keep original)
            complexity_score: int 1-10
            tier:             "cheap" | "mid" | "premium"
            routed:           True if model was changed
            reason:           human-readable explanation
        """
        t0 = time.monotonic()
        score = self.classifier.score(prompt_text, messages)

        # Determine tier from score
        tier_label = "premium"
        for tier_key in ("low", "medium", "high"):
            tier_def = self.routes.get(tier_key, {})
            if score <= tier_def.get("max_score", 0):
                tier_label = tier_def.get("label", tier_key)
                break

        # Look up the replacement model
        provider_key = self._detect_provider(provider_url)
        provider_models = self.model_map.get(provider_key, self.model_map["default"])
        replacement_model = provider_models.get(tier_label)

        # Don't route if:
        # - tier is premium (None means keep original)
        # - replacement is the same as original
        routed = replacement_model is not None and replacement_model != original_model

        elapsed_us = (time.monotonic() - t0) * 1_000_000  # microseconds

        reason = (
            f"score={score}/10 -> {tier_label} tier, "
            f"model {'changed to ' + replacement_model if routed else 'kept as ' + original_model} "
            f"({elapsed_us:.0f}us)"
        )

        # Update stats
        with self._lock:
            self._total_requests += 1
            self._stats[tier_label] = self._stats.get(tier_label, 0) + 1
            if routed:
                self._total_routed += 1

        logger.debug("Router decision: %s", reason)

        return {
            "model": replacement_model if routed else None,
            "complexity_score": score,
            "tier": tier_label,
            "routed": routed,
            "reason": reason,
        }

    def get_stats(self) -> dict[str, Any]:
        """Return routing statistics and estimated savings.

        Savings estimate assumes cheap models cost ~10x less than premium,
        and mid-tier costs ~3x less.
        """
        with self._lock:
            stats = dict(self._stats)
            total = self._total_requests
            total_routed = self._total_routed

        # Rough savings multipliers (premium = 1.0 baseline)
        cost_ratios = {"cheap": 0.05, "mid": 0.30, "premium": 1.0}

        estimated_savings_pct = 0.0
        if total > 0:
            weighted_cost = sum(
                stats.get(tier, 0) * ratio
                for tier, ratio in cost_ratios.items()
            )
            baseline_cost = total * 1.0  # if everything went to premium
            estimated_savings_pct = (1.0 - weighted_cost / baseline_cost) * 100

        return {
            "total_requests": total,
            "total_routed": total_routed,
            "tier_breakdown": stats,
            "estimated_savings_pct": round(estimated_savings_pct, 1),
        }

    # -- Internal -----------------------------------------------------------

    @staticmethod
    def _detect_provider(provider_url: str) -> str:
        """Extract provider key from the upstream URL.

        Examples:
            https://api.openai.com       -> "openai"
            https://api.anthropic.com     -> "anthropic"
            https://api.nousresearch.com  -> "nousresearch"
            https://openrouter.ai/api     -> "openrouter"
        """
        url = provider_url.lower()
        if "openai" in url and "openrouter" not in url:
            return "openai"
        if "anthropic" in url:
            return "anthropic"
        if "nousresearch" in url or "nous" in url:
            return "nousresearch"
        if "openrouter" in url:
            return "openrouter"
        if "googleapis" in url or "generativelanguage" in url:
            return "google"
        if "deepseek" in url:
            return "deepseek"
        if "mistral" in url:
            return "mistral"
        if "ollama" in url or "11434" in url:
            return "ollama"
        return "default"
