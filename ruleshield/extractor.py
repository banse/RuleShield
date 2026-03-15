"""RuleShield Hermes -- Auto rule extraction and prompt feature extraction.

Provides two classes:

* ``PromptExtractor`` -- deterministic hashing and message flattening
  (backward-compatible with the original stub).
* ``RuleExtractor`` -- buffers request/response pairs and generates
  candidate rules by grouping similar prompts and checking response
  consistency.

Extraction heuristic (intentionally simple for hackathon scope):
  1. Group buffered samples by the first 3 words of the user message.
  2. Discard groups smaller than *min_samples*.
  3. For qualifying groups, check that responses share > 60% of their
     words (i.e., the LLM gives a consistent answer).
  4. Extract common keywords to build ``contains`` patterns.
  5. Emit candidate rules with the most frequent response as the
     pre-computed answer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from collections import Counter, defaultdict
from typing import Any

logger = logging.getLogger("ruleshield.extractor")


# ---------------------------------------------------------------------------
# PromptExtractor (backward-compatible with original stub)
# ---------------------------------------------------------------------------

class PromptExtractor:
    """Extracts features from prompts for cache matching and rule evaluation."""

    async def init(self) -> None:
        """Load any required models (e.g. sentence-transformers)."""
        pass

    def hash_prompt(self, prompt_text: str) -> str:
        """Return a deterministic hash of the prompt text."""
        return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

    async def embed(self, prompt_text: str) -> list[float]:
        """Return a semantic embedding vector for the prompt.

        Embedding support is optional -- returns an empty list when no
        embedding model is loaded.
        """
        return []

    def extract_messages_text(self, messages: list[dict[str, Any]]) -> str:
        """Flatten an OpenAI messages array into a single string."""
        parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(f"{role}: {content}")
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(f"{role}: {part['text']}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenization (alphanumeric only)."""
    return _WORD_RE.findall(text.lower())


def _first_n_words(text: str, n: int = 3) -> str:
    """Return the first *n* lowercased words as a grouping key."""
    words = _tokenize(text)
    return " ".join(words[:n])


def _word_overlap(a: str, b: str) -> float:
    """Return the Jaccard-like word overlap ratio between two strings."""
    words_a = set(_tokenize(a))
    words_b = set(_tokenize(b))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _extract_last_user_message(messages: list[dict[str, Any]] | None) -> str:
    """Pull last user message from a messages list."""
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


# ---------------------------------------------------------------------------
# RuleExtractor
# ---------------------------------------------------------------------------

class RuleExtractor:
    """Buffers LLM request/response pairs and extracts candidate rules.

    Usage::

        extractor = RuleExtractor()
        await extractor.feed(prompt, messages, response, model)
        # ... feed more samples ...
        candidates = await extractor.extract_rules(min_samples=3)
    """

    def __init__(self) -> None:
        self.pending: list[dict[str, Any]] = []
        self._candidates: list[dict[str, Any]] = []

    async def feed(
        self,
        prompt_text: str,
        messages: list[dict[str, Any]] | None,
        response_text: str,
        model: str,
    ) -> None:
        """Buffer a single request/response observation."""
        user_msg = _extract_last_user_message(messages) or prompt_text
        self.pending.append(
            {
                "user_message": user_msg,
                "prompt_text": prompt_text,
                "response_text": response_text,
                "model": model,
            }
        )

    async def extract_rules(self, min_samples: int = 3) -> list[dict[str, Any]]:
        """Analyze buffered samples and return candidate rules.

        Steps:
          1. Group by first-3-words key.
          2. Filter groups with fewer than *min_samples* entries.
          3. Check pairwise response consistency (> 60% word overlap).
          4. Build ``contains`` patterns from common keywords.
          5. Return candidate rule dicts ready for ``RuleEngine.add_rule``.
        """
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in self.pending:
            key = _first_n_words(entry["user_message"])
            if key:
                groups[key].append(entry)

        candidates: list[dict[str, Any]] = []

        for key, entries in groups.items():
            if len(entries) < min_samples:
                continue

            # Check response consistency.
            responses = [e["response_text"] for e in entries]
            if not self._responses_consistent(responses):
                continue

            # Pick the most common response as the canonical answer.
            canonical_response = Counter(responses).most_common(1)[0][0]

            # Extract keyword patterns from user messages.
            patterns = self._extract_patterns(entries)
            if not patterns:
                continue

            # Estimate max message length for a condition.
            max_len = max(len(e["user_message"]) for e in entries)
            # Add a small buffer so near-length messages still match.
            max_len_cond = max_len + 10

            rule_id = f"auto_{uuid.uuid4().hex[:8]}"
            rule: dict[str, Any] = {
                "id": rule_id,
                "name": f"Auto-extracted: {key}",
                "description": f"Auto-generated from {len(entries)} similar requests.",
                "patterns": patterns,
                "conditions": [
                    {"type": "max_length", "value": max_len_cond, "field": "last_user_message"},
                ],
                "response": {
                    "content": canonical_response,
                    "model": "ruleshield-rule",
                },
                "confidence": 0.5,
                "priority": 1,
                "enabled": False,
                "hit_count": 0,
                "auto_generated": True,
                "sample_count": len(entries),
            }
            candidates.append(rule)

        self._candidates = candidates
        return candidates

    async def get_candidates(self) -> list[dict[str, Any]]:
        """Return the most recently extracted candidate rules."""
        return list(self._candidates)

    async def save_candidates(self, rules_dir: str) -> int:
        """Save extracted rule candidates as disabled rules.

        Candidates are saved to ``rules_dir/candidates/`` directory with
        ``enabled=false`` and ``confidence=0.5``.  They will be auto-activated
        when feedback and shadow comparisons confirm their accuracy.

        Returns the number of candidates saved.
        """
        if not self._candidates:
            return 0

        candidates_dir = os.path.join(os.path.expanduser(rules_dir), "candidates")
        os.makedirs(candidates_dir, exist_ok=True)

        saved = 0
        for candidate in self._candidates:
            # Ensure candidates start disabled with low confidence.
            candidate["enabled"] = False
            candidate["confidence"] = 0.5

            filepath = os.path.join(candidates_dir, f"{candidate['id']}.json")

            # Do not overwrite existing candidate files.
            if os.path.exists(filepath):
                logger.debug(
                    "Candidate %s already exists at %s, skipping",
                    candidate["id"],
                    filepath,
                )
                continue

            try:
                with open(filepath, "w", encoding="utf-8") as fh:
                    json.dump(candidate, fh, indent=2, ensure_ascii=False)
                saved += 1
                logger.info(
                    "Saved candidate rule %s to %s",
                    candidate["id"],
                    filepath,
                )
            except OSError as exc:
                logger.warning(
                    "Failed to save candidate %s: %s", candidate["id"], exc
                )

        return saved

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _responses_consistent(responses: list[str], threshold: float = 0.6) -> bool:
        """Return True if pairwise word overlap exceeds *threshold* on average."""
        if len(responses) < 2:
            return True
        overlaps: list[float] = []
        # Sample pairwise comparisons (cap at 20 pairs for speed).
        pairs_checked = 0
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                overlaps.append(_word_overlap(responses[i], responses[j]))
                pairs_checked += 1
                if pairs_checked >= 20:
                    break
            if pairs_checked >= 20:
                break
        if not overlaps:
            return False
        return (sum(overlaps) / len(overlaps)) >= threshold

    @staticmethod
    def _extract_patterns(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Build ``contains`` patterns from the most common keywords.

        Ignores very short stopwords and picks keywords that appear in the
        majority (> 50%) of the user messages.
        """
        stopwords = {
            "a", "an", "the", "is", "it", "to", "of", "in", "on", "at",
            "and", "or", "but", "for", "i", "me", "my", "you", "your",
            "we", "do", "can", "this", "that", "what", "how",
        }
        word_counts: Counter[str] = Counter()
        total = len(entries)

        for entry in entries:
            unique_words = set(_tokenize(entry["user_message"]))
            for w in unique_words:
                if len(w) > 2 and w not in stopwords:
                    word_counts[w] += 1

        # Keep words appearing in > 50% of messages.
        threshold = total * 0.5
        keywords = [w for w, c in word_counts.most_common(10) if c >= threshold]

        patterns: list[dict[str, Any]] = []
        for kw in keywords[:5]:  # Cap at 5 patterns per rule.
            patterns.append(
                {"type": "contains", "value": kw, "field": "last_user_message"}
            )
        return patterns
