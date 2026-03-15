#!/usr/bin/env python3
"""RuleShield Rule Suggestion Script.

Reads request_log from ~/.ruleshield/cache.db, groups similar prompts,
and suggests new rules for prompts that recur with consistent responses.
Uses plain print() only (no Rich).
"""

import json
import re
import sqlite3
import uuid
from collections import Counter, defaultdict
from pathlib import Path

DB_PATH = Path.home() / ".ruleshield" / "cache.db"
RULES_DIR = Path.home() / ".ruleshield" / "rules"

_WORD_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "an", "the", "is", "it", "to", "of", "in", "on", "at",
    "and", "or", "but", "for", "i", "me", "my", "you", "your",
    "we", "do", "can", "this", "that", "what", "how",
}


def tokenize(text):
    """Lowercase word tokenization (alphanumeric only)."""
    return _WORD_RE.findall(text.lower())


def first_n_words(text, n=5):
    """Return the first n lowercased words as a grouping key."""
    words = tokenize(text)
    return " ".join(words[:n])


def word_overlap(a, b):
    """Jaccard-like word overlap ratio between two strings."""
    words_a = set(tokenize(a))
    words_b = set(tokenize(b))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def load_existing_rule_patterns():
    """Load pattern values from existing rules to avoid suggesting duplicates."""
    existing = set()
    if not RULES_DIR.exists():
        return existing
    for f in RULES_DIR.glob("*.json"):
        try:
            with open(f) as fh:
                rules = json.load(fh)
                if isinstance(rules, list):
                    for rule in rules:
                        for p in rule.get("patterns", []):
                            existing.add(p.get("value", "").lower())
                elif isinstance(rules, dict):
                    for p in rules.get("patterns", []):
                        existing.add(p.get("value", "").lower())
        except (json.JSONDecodeError, KeyError, IOError):
            continue
    return existing


def suggest():
    if not DB_PATH.exists():
        print("RuleShield database not found at {}".format(DB_PATH))
        print("No request history to analyze.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()

        # Get LLM requests -- these are the ones that could benefit from rules
        cur.execute("""
            SELECT prompt_text, response, model
            FROM request_log
            WHERE resolution_type = 'llm'
              AND prompt_text IS NOT NULL
              AND prompt_text != ''
            ORDER BY created_at DESC
            LIMIT 500
        """)
        rows = cur.fetchall()

        if not rows:
            print("No LLM requests found in history.")
            print("Send some requests through RuleShield first.")
            return

        # Group by first 5 words
        groups = defaultdict(list)
        for row in rows:
            key = first_n_words(row["prompt_text"])
            if key:
                groups[key].append({
                    "prompt": row["prompt_text"],
                    "response": row["response"] or "",
                    "model": row["model"] or "unknown",
                })

        existing_patterns = load_existing_rule_patterns()
        suggestions = []

        for key, entries in groups.items():
            if len(entries) < 3:
                continue

            # Check response consistency via pairwise word overlap
            responses = [e["response"] for e in entries]
            overlaps = []
            for i in range(min(len(responses), 5)):
                for j in range(i + 1, min(len(responses), 5)):
                    overlaps.append(word_overlap(responses[i], responses[j]))

            if not overlaps:
                continue

            avg_overlap = sum(overlaps) / len(overlaps)
            if avg_overlap < 0.5:
                continue

            # Most common response becomes the canonical answer
            canonical = Counter(responses).most_common(1)[0][0]

            # Extract keyword patterns from user messages
            word_counts = Counter()
            for entry in entries:
                unique = set(tokenize(entry["prompt"]))
                for w in unique:
                    if len(w) > 2 and w not in STOPWORDS:
                        word_counts[w] += 1

            threshold = len(entries) * 0.5
            keywords = [w for w, c in word_counts.most_common(10) if c >= threshold]

            # Skip if all keywords already exist in current rules
            new_keywords = [k for k in keywords if k not in existing_patterns]
            if not new_keywords and keywords:
                continue

            patterns = []
            for kw in (new_keywords or keywords)[:5]:
                patterns.append({
                    "type": "contains",
                    "value": kw,
                    "field": "last_user_message",
                })

            if not patterns:
                continue

            max_len = max(len(e["prompt"]) for e in entries) + 10
            confidence = min(0.95, 0.5 + (avg_overlap * 0.3) + (len(entries) / 50))

            rule_id = "suggested_{}".format(uuid.uuid4().hex[:8])
            suggestion = {
                "id": rule_id,
                "name": "Suggested: {}".format(key),
                "description": "Auto-suggested from {} similar LLM requests (overlap: {:.0%})".format(
                    len(entries), avg_overlap
                ),
                "patterns": patterns,
                "conditions": [
                    {"type": "max_length", "value": max_len, "field": "last_user_message"},
                ],
                "response": {
                    "content": canonical[:500] if len(canonical) > 500 else canonical,
                    "model": "ruleshield-rule",
                },
                "confidence": round(confidence, 2),
                "priority": 5,
                "enabled": True,
                "hit_count": 0,
                "sample_count": len(entries),
            }
            suggestions.append(suggestion)

        # Print results
        print("=" * 60)
        print("  RULESHIELD RULE SUGGESTIONS")
        print("=" * 60)
        print()

        if not suggestions:
            print("  No rule suggestions at this time.")
            print("  Need at least 3 similar LLM requests with consistent responses.")
            print()
        else:
            print("  Found {} potential rule(s):".format(len(suggestions)))
            print()

            for i, s in enumerate(suggestions, 1):
                print("  --- Suggestion {} ---".format(i))
                print("  Name:       {}".format(s["name"]))
                print("  Confidence: {:.0%}".format(s["confidence"]))
                print("  Samples:    {}".format(s["sample_count"]))
                print("  Patterns:   {}".format(
                    ", ".join(p["value"] for p in s["patterns"])
                ))
                response_preview = s["response"]["content"][:80]
                if len(s["response"]["content"]) > 80:
                    response_preview += "..."
                print("  Response:   {}".format(response_preview))
                print()

            print("-" * 60)
            print("  RULE JSON (copy to ~/.ruleshield/rules/suggested.json)")
            print("-" * 60)
            print(json.dumps(suggestions, indent=2))

        print()
        print("=" * 60)

    except sqlite3.OperationalError as e:
        print("Database error: {}".format(e))
    finally:
        conn.close()


if __name__ == "__main__":
    suggest()
