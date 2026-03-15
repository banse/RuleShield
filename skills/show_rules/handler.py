"""RuleShield Hermes Skill -- Show Rules Handler.

Reads JSON rule files from the RuleShield rules directory and prints
a formatted summary of each rule including patterns, hit counts,
confidence scores, and status.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RULES_DIR = Path.home() / ".ruleshield" / "rules"


def load_rules() -> list[dict]:
    """Load all rules from JSON files in the rules directory."""
    rules: list[dict] = []

    if not RULES_DIR.exists():
        return rules

    for fp in sorted(RULES_DIR.glob("*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                rules.extend(data)
            elif isinstance(data, dict):
                rules.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    # Sort by priority descending
    rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
    return rules


def format_patterns(patterns: list[dict]) -> str:
    """Format pattern list into a readable string."""
    if not patterns:
        return "(none)"

    parts = []
    for p in patterns[:3]:  # Show first 3
        ptype = p.get("type", "?")
        value = p.get("value", "")
        if len(value) > 25:
            value = value[:22] + "..."
        parts.append(f'{ptype}:"{value}"')

    result = ", ".join(parts)
    remaining = len(patterns) - 3
    if remaining > 0:
        result += f" (+{remaining} more)"
    return result


def main() -> None:
    """Print a formatted summary of all loaded rules."""
    rules = load_rules()

    if not rules:
        print("RuleShield Rules")
        print("=" * 40)
        print()
        print("No rules found.")
        print(f"Expected rules at: {RULES_DIR}")
        print("Run 'ruleshield init' to set up default rules.")
        return

    print()
    print("RuleShield Learned Rules")
    print("=" * 65)
    print()

    active = 0
    total_hits = 0

    for idx, rule in enumerate(rules, 1):
        name = rule.get("name", rule.get("id", "unnamed"))
        rule_id = rule.get("id", "?")
        description = rule.get("description", "")
        patterns = rule.get("patterns", [])
        hit_count = rule.get("hit_count", 0)
        confidence = rule.get("confidence", 1.0)
        enabled = rule.get("enabled", True)
        priority = rule.get("priority", 0)
        auto = rule.get("auto_generated", False)

        status = "ENABLED" if enabled else "DISABLED"
        if enabled:
            active += 1
        total_hits += hit_count

        conf_pct = f"{confidence * 100:.0f}%"
        tag = " [auto]" if auto else ""

        print(f"  {idx}. {name}{tag}")
        print(f"     ID: {rule_id}  |  Priority: {priority}  |  Status: {status}")
        if description:
            print(f"     {description}")
        print(f"     Patterns: {format_patterns(patterns)}")
        print(f"     Hits: {hit_count}  |  Confidence: {conf_pct}")
        print()

    print("-" * 65)
    print(f"  {active}/{len(rules)} rules active  |  {total_hits} total hits")
    print(f"  Rules directory: {RULES_DIR}")
    print()


if __name__ == "__main__":
    main()
