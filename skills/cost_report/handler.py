"""RuleShield Hermes Skill -- Cost Report Handler.

Reads the RuleShield SQLite database and prints a formatted cost savings
summary for the Hermes Agent to display to the user.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".ruleshield" / "cache.db"


def get_stats() -> dict:
    """Query aggregated stats from the request_log table."""
    stats = {
        "total_requests": 0,
        "cache_hits": 0,
        "rule_hits": 0,
        "llm_calls": 0,
        "total_cost": 0.0,
        "llm_cost": 0.0,
        "saved": 0.0,
        "savings_pct": 0.0,
        "top_rules": [],
    }

    if not DB_PATH.exists():
        return stats

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM request_log")
    stats["total_requests"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM request_log WHERE resolution_type = 'cache'")
    stats["cache_hits"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM request_log WHERE resolution_type = 'rule'")
    stats["rule_hits"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM request_log WHERE resolution_type = 'llm'")
    stats["llm_calls"] = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM request_log")
    stats["total_cost"] = round(float(cur.fetchone()[0]), 4)

    cur.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM request_log WHERE resolution_type = 'llm'")
    stats["llm_cost"] = round(float(cur.fetchone()[0]), 4)

    stats["saved"] = round(stats["total_cost"] - stats["llm_cost"], 4)

    if stats["total_cost"] > 0:
        stats["savings_pct"] = round(stats["saved"] / stats["total_cost"] * 100, 1)

    # Top rules by frequency -- join not available, so estimate from resolution_type
    # We track rule hits from the request_log prompt patterns
    try:
        cur.execute(
            """
            SELECT prompt_text, COUNT(*) as cnt
            FROM request_log
            WHERE resolution_type = 'rule'
            GROUP BY prompt_text
            ORDER BY cnt DESC
            LIMIT 5
            """
        )
        stats["top_rules"] = [
            {"prompt": row[0][:50] if row[0] else "unknown", "hits": row[1]}
            for row in cur.fetchall()
        ]
    except Exception:
        pass

    conn.close()
    return stats


def format_pct(part: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{round(part / total * 100)}%"


def main() -> None:
    """Print a formatted cost savings report."""
    stats = get_stats()

    total = stats["total_requests"]

    if total == 0:
        print("RuleShield Cost Report")
        print("=" * 40)
        print()
        print("No requests recorded yet.")
        print("Start the proxy with: ruleshield start")
        return

    cache = stats["cache_hits"]
    rule = stats["rule_hits"]
    llm = stats["llm_calls"]
    saved = stats["saved"]
    savings_pct = stats["savings_pct"]

    print()
    print("RuleShield Cost Savings Report")
    print("=" * 45)
    print()
    print(f"  Total Requests:    {total}")
    print(f"  Cache Hits:        {cache}  ({format_pct(cache, total)})")
    print(f"  Rule Hits:         {rule}  ({format_pct(rule, total)})")
    print(f"  LLM Calls:         {llm}  ({format_pct(llm, total)})")
    print()
    print(f"  Estimated Cost:    ${stats['total_cost']:.4f}")
    print(f"  Actual LLM Cost:   ${stats['llm_cost']:.4f}")
    print(f"  Total Saved:       ${saved:.4f}  ({savings_pct:.1f}%)")
    print()

    # Visual savings bar
    bar_width = 30
    filled = int(round(savings_pct / 100 * bar_width))
    empty = bar_width - filled
    bar = "#" * filled + "." * empty
    print(f"  Savings: [{bar}] {savings_pct:.1f}%")
    print()

    # Top rules
    if stats["top_rules"]:
        print("  Top Rule Matches:")
        print("  " + "-" * 40)
        for entry in stats["top_rules"]:
            prompt = entry["prompt"][:40]
            hits = entry["hits"]
            print(f"    {hits:>4}x  {prompt}")
        print()

    print("=" * 45)
    print()


if __name__ == "__main__":
    main()
