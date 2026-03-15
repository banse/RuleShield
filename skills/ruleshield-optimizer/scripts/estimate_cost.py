#!/usr/bin/env python3
"""RuleShield Cost Estimation Script.

Takes a prompt as argv[1], estimates token count and cost,
and checks whether cache or rules would handle it.
Uses plain print() only (no Rich).
"""

import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".ruleshield" / "cache.db"
RULES_DIR = Path.home() / ".ruleshield" / "rules"

# Approximate pricing (per token)
INPUT_COST_PER_TOKEN = 0.005 / 1000   # $0.005 per 1k input tokens
OUTPUT_COST_PER_TOKEN = 0.015 / 1000  # $0.015 per 1k output tokens
AVG_OUTPUT_RATIO = 1.5  # Typical output is ~1.5x the input token count


def estimate_tokens(text):
    """Estimate token count: words * 1.3 is a reasonable approximation."""
    words = len(text.split())
    return max(1, int(words * 1.3))


def compute_hash(text):
    """SHA-256 hash of prompt text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_cache(prompt_hash):
    """Check if prompt hash exists in cache. Returns True if found."""
    if not DB_PATH.exists():
        return False
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM cache WHERE prompt_hash = ?", (prompt_hash,))
        result = cur.fetchone() is not None
        conn.close()
        return result
    except sqlite3.OperationalError:
        return False


def check_rules(prompt_text):
    """Check if any rule would match the prompt. Returns rule name or None."""
    if not RULES_DIR.exists():
        return None

    text_lower = prompt_text.lower().strip()

    for f in sorted(RULES_DIR.glob("*.json")):
        try:
            with open(f) as fh:
                rules = json.load(fh)
                if not isinstance(rules, list):
                    rules = [rules]
        except (json.JSONDecodeError, IOError):
            continue

        for rule in rules:
            if not rule.get("enabled", True):
                continue

            # Check conditions first (e.g., max_length)
            conditions_met = True
            for cond in rule.get("conditions", []):
                if cond.get("type") == "max_length":
                    if len(text_lower) > cond.get("value", 9999):
                        conditions_met = False
                        break
            if not conditions_met:
                continue

            # Check patterns -- any single match is sufficient
            for pattern in rule.get("patterns", []):
                ptype = pattern.get("type", "")
                pvalue = pattern.get("value", "").lower()

                matched = False
                if ptype == "exact" and text_lower == pvalue:
                    matched = True
                elif ptype == "contains" and pvalue in text_lower:
                    matched = True
                elif ptype == "regex":
                    try:
                        if re.match(pvalue, text_lower):
                            matched = True
                    except re.error:
                        continue

                if matched:
                    return rule.get("name", rule.get("id", "unknown"))

    return None


def estimate(prompt_text):
    """Estimate cost and predict resolution for a given prompt."""
    prompt_hash = compute_hash(prompt_text)
    tokens_in = estimate_tokens(prompt_text)
    tokens_out_est = int(tokens_in * AVG_OUTPUT_RATIO)

    cost_input = tokens_in * INPUT_COST_PER_TOKEN
    cost_output = tokens_out_est * OUTPUT_COST_PER_TOKEN
    estimated_cost = cost_input + cost_output

    would_cache = check_cache(prompt_hash)
    matching_rule = check_rules(prompt_text)

    if would_cache:
        prediction = "CACHE HIT -- $0.00 (free)"
    elif matching_rule:
        prediction = "RULE MATCH ({}) -- $0.00 (free)".format(matching_rule)
    else:
        prediction = "LLM CALL -- ~${:.6f}".format(estimated_cost)

    # Print report
    print("=" * 60)
    print("  RULESHIELD COST ESTIMATE")
    print("=" * 60)
    print()
    prompt_display = prompt_text[:60]
    if len(prompt_text) > 60:
        prompt_display += "..."
    print("  Prompt:              {}".format(prompt_display))
    print("  Prompt Hash:         {}...".format(prompt_hash[:16]))
    print("  Est. Input Tokens:   {}".format(tokens_in))
    print("  Est. Output Tokens:  {}".format(tokens_out_est))
    print()
    print("  Full LLM Cost:       ${:.6f}".format(estimated_cost))
    print("  Cache Hit:           {}".format("Yes" if would_cache else "No"))
    print("  Rule Match:          {}".format(matching_rule or "None"))
    print()
    print("  >> PREDICTION: {}".format(prediction))
    if would_cache or matching_rule:
        print("  >> SAVINGS:    ${:.6f} saved!".format(estimated_cost))
    print()
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python estimate_cost.py \"your prompt text here\"")
        sys.exit(1)
    estimate(sys.argv[1])
