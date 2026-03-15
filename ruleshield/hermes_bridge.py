"""Bridge to Hermes Agent Python Library for smart request handling.

When a request is too complex for rules but doesn't need the full
premium LLM, RuleShield can delegate to a local Hermes Agent instance
running a cheaper model. This saves cost while maintaining quality
for medium-complexity tasks.

OPTIONAL: Only activates if hermes-agent is installed.

Architecture (Layer 2.5):
    Layer 1: Semantic Cache  (exact/fuzzy match -> instant)
    Layer 2: Rule Engine     (pattern match -> instant)
  * Layer 2.5: Hermes Bridge (partial confidence -> cheap local LLM)
    Layer 3: Upstream LLM    (full passthrough -> expensive)

The bridge handles requests where rules have PARTIAL confidence
(0.5-0.85). Instead of sending the full request to the expensive
upstream LLM, we strip the known context and send only the "hard part"
to a local Hermes agent running a cheap model.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

logger = logging.getLogger("ruleshield.hermes_bridge")

# Confidence thresholds for bridge activation.
PARTIAL_CONFIDENCE_MIN = 0.5
PARTIAL_CONFIDENCE_MAX = 0.85


class HermesBridge:
    """Manages a local Hermes Agent instance for mid-tier request handling.

    The bridge is entirely optional. If hermes-agent is not installed,
    or if the bridge is disabled in config, all methods gracefully return
    None and the proxy falls through to the upstream LLM as usual.
    """

    def __init__(self, model: str = "claude-haiku-4-5", enabled: bool = False):
        self.enabled = enabled
        self.model = model
        self._agent: Any = None
        self._available = False
        self._requests_handled = 0
        self._tokens_saved = 0
        self._total_latency_ms = 0.0

    async def init(self) -> None:
        """Try to import and initialize Hermes Agent.

        Gracefully disables the bridge if hermes-agent is not installed
        or if initialization fails for any reason.
        """
        if not self.enabled:
            logger.info("Hermes bridge disabled in config.")
            return

        try:
            from run_agent import AIAgent  # type: ignore[import-untyped]

            self._agent = AIAgent(
                model=self.model,
                quiet_mode=True,
                skip_context_files=True,
                skip_memory=True,
                max_iterations=10,  # limit cost
                disabled_toolsets=["terminal", "browser"],  # safety
            )
            self._available = True
            logger.info(
                "Hermes bridge initialized with model=%s", self.model
            )
        except ImportError:
            self._available = False
            logger.info(
                "hermes-agent not installed -- bridge disabled. "
                "Install with: pip install hermes-agent"
            )
        except Exception as exc:
            self._available = False
            logger.warning(
                "Hermes bridge initialization failed: %s", exc
            )

    @property
    def available(self) -> bool:
        """True only when the bridge is both enabled and has a working agent."""
        return self._available and self.enabled

    def should_handle(self, confidence: float) -> bool:
        """Decide whether a partial-confidence rule match should use the bridge.

        Args:
            confidence: The rule engine's confidence score (0.0-1.0).

        Returns:
            True if the confidence falls in the partial range and the
            bridge is available.
        """
        if not self.available:
            return False
        return PARTIAL_CONFIDENCE_MIN <= confidence <= PARTIAL_CONFIDENCE_MAX

    async def handle(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None = None,
        context_hint: str | None = None,
    ) -> dict[str, Any] | None:
        """Send a request to the local Hermes Agent.

        Args:
            prompt_text: The user's question/request.
            messages: Full conversation history (optional, not currently
                      forwarded to keep the bridge call lightweight).
            context_hint: What RuleShield already knows about this request
                         (e.g. "This is a status check, but with custom params").

        Returns:
            A dict with the response payload, or None if the bridge is
            not available or the call fails.
        """
        if not self.available:
            return None

        t_start = time.monotonic()

        # Build the prompt for the cheap model.
        augmented_prompt = prompt_text
        if context_hint:
            augmented_prompt = (
                f"Context: {context_hint}\n\n"
                f"Question: {prompt_text}"
            )

        try:
            response_text = self._agent.chat(augmented_prompt)
            latency_ms = (time.monotonic() - t_start) * 1000

            # Estimate tokens (rough: ~1.3 tokens per word).
            prompt_tokens = int(len(augmented_prompt.split()) * 1.3)
            completion_tokens = int(len(str(response_text).split()) * 1.3)
            total_tokens = prompt_tokens + completion_tokens

            self._requests_handled += 1
            self._total_latency_ms += latency_ms
            # Estimate tokens saved vs sending full prompt to expensive model.
            self._tokens_saved += total_tokens

            result = {
                "content": str(response_text),
                "model": f"hermes-bridge-{self.model}",
                "tokens": total_tokens,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
                "latency_ms": latency_ms,
            }

            logger.debug(
                "Hermes bridge handled request in %.1fms (%d tokens)",
                latency_ms,
                total_tokens,
            )
            return result

        except Exception as exc:
            logger.warning("Hermes bridge call failed: %s", exc)
            return None

    async def handle_trimmed(
        self,
        full_prompt: str,
        known_parts: list[dict[str, str]],
        unknown_part: str,
    ) -> dict[str, Any] | None:
        """Handle a request where some parts are already answered by rules.

        Constructs a trimmed prompt that includes the known context as
        background and asks the cheap model to answer only the remaining
        unknown part.

        Args:
            full_prompt: Original full prompt from the user.
            known_parts: Parts already answered by rules. Each dict has
                         keys "question", "answer", and optionally "rule_id".
            unknown_part: The remaining part that needs LLM intelligence.

        Returns:
            A dict with the response payload, or None if unavailable.
        """
        if not self.available:
            return None

        if not unknown_part.strip():
            return None

        # Build the trimmed prompt with known context.
        context_lines = []
        for part in known_parts:
            q = part.get("question", "")
            a = part.get("answer", "")
            if q and a:
                context_lines.append(f"- Q: {q}\n  A: {a}")

        if context_lines:
            context_block = "\n".join(context_lines)
            trimmed_prompt = (
                f"Context (already known):\n"
                f"{context_block}\n\n"
                f"Please answer ONLY this remaining question:\n"
                f"{unknown_part}"
            )
        else:
            trimmed_prompt = unknown_part

        context_hint = (
            f"Original prompt had {len(known_parts)} part(s) already "
            f"answered by rules. Answering the remaining part only."
        )

        return await self.handle(
            prompt_text=trimmed_prompt,
            context_hint=context_hint,
        )

    def format_openai_response(
        self,
        bridge_result: dict[str, Any],
        original_model: str = "unknown",
    ) -> dict[str, Any]:
        """Wrap a bridge result in an OpenAI-compatible chat completion response.

        This allows the proxy to return the bridge response in the same
        format that clients expect from the upstream LLM.
        """
        return {
            "id": f"ruleshield-bridge-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": bridge_result.get("model", f"hermes-bridge-{self.model}"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": bridge_result.get("content", ""),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": bridge_result.get("usage", {}),
        }

    def get_stats(self) -> dict[str, Any]:
        """Return bridge usage statistics."""
        avg_latency = 0.0
        if self._requests_handled > 0:
            avg_latency = self._total_latency_ms / self._requests_handled

        return {
            "available": self._available,
            "enabled": self.enabled,
            "model": self.model,
            "requests_handled": self._requests_handled,
            "tokens_saved_estimate": self._tokens_saved,
            "avg_latency_ms": round(avg_latency, 1),
        }


# ---------------------------------------------------------------------------
# Prompt trimming utility
# ---------------------------------------------------------------------------


def trim_prompt(
    full_prompt: str,
    rule_matches: list[dict[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    """Split a prompt into known (rule-handled) and unknown parts.

    Strategy:
      1. Split prompt into sentences using punctuation boundaries.
      2. Check each sentence against rule match patterns.
      3. Separate into known_parts (have rule answers) and unknown_parts.
      4. Return (trimmed_prompt, known_parts).

    Args:
        full_prompt: The full user prompt text.
        rule_matches: List of partial rule matches. Each dict should have:
            - "patterns": list of pattern strings that matched
            - "answer": the rule's pre-computed answer
            - "rule_id": identifier for the rule (optional)

    Returns:
        A tuple of (trimmed_prompt, known_parts) where trimmed_prompt
        contains only the sentences not covered by rules, and known_parts
        is a list of dicts with "question" and "answer" keys.

    Example::

        >>> prompt = "Check server status and analyze the error logs from today"
        >>> matches = [
        ...     {
        ...         "patterns": ["server status", "check server"],
        ...         "answer": "Server is running normally",
        ...         "rule_id": "server_status",
        ...     }
        ... ]
        >>> trimmed, known = trim_prompt(prompt, matches)
        >>> trimmed
        'analyze the error logs from today'
        >>> known
        [{'question': 'Check server status', 'answer': 'Server is running normally', 'rule_id': 'server_status'}]
    """
    if not rule_matches:
        return full_prompt, []

    # Split on sentence boundaries: period, question mark, exclamation,
    # semicolon, or "and"/"then" acting as clause separators.
    sentences = _split_into_clauses(full_prompt)

    known_parts: list[dict[str, str]] = []
    unknown_parts: list[str] = []

    for sentence in sentences:
        sentence_stripped = sentence.strip()
        if not sentence_stripped:
            continue

        matched_rule = _find_matching_rule(sentence_stripped, rule_matches)
        if matched_rule is not None:
            known_parts.append({
                "question": sentence_stripped,
                "answer": matched_rule.get("answer", ""),
                "rule_id": matched_rule.get("rule_id", ""),
            })
        else:
            unknown_parts.append(sentence_stripped)

    trimmed = " ".join(unknown_parts).strip()

    # If everything was matched (or nothing was), return accordingly.
    if not trimmed:
        trimmed = full_prompt  # nothing to trim, fall back to full prompt

    return trimmed, known_parts


def _split_into_clauses(text: str) -> list[str]:
    """Split text into clauses on sentence boundaries and conjunctions.

    Handles:
      - Standard sentence endings (. ? ! ;)
      - Coordinating conjunctions used as clause separators ("and", "then",
        "also", "plus")
      - Comma-separated clauses when they look like independent requests
    """
    # Split on sentence-ending punctuation first.
    parts = re.split(r'[.?!;]\s*', text)

    # Further split on conjunctions that separate independent clauses.
    result: list[str] = []
    conjunction_pattern = re.compile(
        r'\b(?:and\s+(?:also\s+)?|then\s+|also\s+|plus\s+)', re.IGNORECASE
    )
    for part in parts:
        sub_parts = conjunction_pattern.split(part)
        result.extend(sub_parts)

    return [p.strip() for p in result if p.strip()]


def _find_matching_rule(
    sentence: str,
    rule_matches: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Check if a sentence is covered by any of the rule matches.

    A sentence is considered "covered" if any of the rule's patterns
    appear as a substring (case-insensitive) in the sentence.
    """
    sentence_lower = sentence.lower()

    for rule in rule_matches:
        patterns = rule.get("patterns", [])
        for pattern in patterns:
            if isinstance(pattern, str) and pattern.lower() in sentence_lower:
                return rule

    return None
