#!/usr/bin/env python3
"""RuleShield Cost Analysis Script.

Connects to ~/.ruleshield/cache.db and prints aggregated cost statistics.
Designed to run inside Hermes Agent -- uses plain print() only (no Rich).
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".ruleshield" / "cache.db"


def get_connection():
    """Return a sqlite3 connection, or None if DB does not exist."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def analyze():
    conn = get_connection()
    if conn is None:
        print("RuleShield database not found at", DB_PATH)
        print("Make sure RuleShield is installed and has processed at least one request.")
        return

    try:
        cur = conn.cursor()

        # Total requests
        cur.execute("SELECT COUNT(*) as cnt FROM request_log")
        total = cur.fetchone()["cnt"]

        if total == 0:
            print("No requests logged yet. Send some requests through RuleShield first.")
            conn.close()
            return

        # Breakdown by resolution type
        cur.execute("""
            SELECT resolution_type, COUNT(*) as cnt,
                   COALESCE(SUM(cost_usd), 0) as total_cost,
                   COALESCE(SUM(tokens_in), 0) as total_tokens_in,
                   COALESCE(SUM(tokens_out), 0) as total_tokens_out,
                   COALESCE(AVG(latency_ms), 0) as avg_latency
            FROM request_log
            GROUP BY resolution_type
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()

        breakdown = {}
        total_cost = 0.0
        for row in rows:
            rtype = row["resolution_type"] or "unknown"
            breakdown[rtype] = {
                "count": row["cnt"],
                "cost": row["total_cost"],
                "tokens_in": row["total_tokens_in"],
                "tokens_out": row["total_tokens_out"],
                "avg_latency_ms": round(row["avg_latency"], 1),
            }
            total_cost += row["total_cost"]

        # Calculate savings: cost of cache+rule hits (would have been LLM calls)
        saved_cost = sum(
            breakdown.get(t, {}).get("cost", 0)
            for t in ("cache", "rule")
        )
        estimated_total_without_shield = total_cost + saved_cost
        savings_pct = (
            saved_cost / estimated_total_without_shield * 100
            if estimated_total_without_shield > 0
            else 0
        )

        # Top cache entries by hit count
        cur.execute("""
            SELECT prompt_text, hit_count, cost_usd, model
            FROM cache
            WHERE hit_count > 0
            ORDER BY hit_count DESC
            LIMIT 5
        """)
        top_cache = cur.fetchall()

        # Top rules by hit frequency in request_log
        cur.execute("""
            SELECT model, COUNT(*) as hits
            FROM request_log
            WHERE resolution_type = 'rule'
            GROUP BY model
            ORDER BY hits DESC
            LIMIT 5
        """)
        top_rules = cur.fetchall()

        # Print report
        print("=" * 60)
        print("  RULESHIELD COST ANALYSIS REPORT")
        print("=" * 60)
        print()
        print("  Total Requests:    {}".format(total))
        print("  Total Cost:        ${:.6f}".format(total_cost))
        print("  Estimated Savings: ${:.6f} ({:.1f}%)".format(saved_cost, savings_pct))
        print()
        print("-" * 60)
        print("  RESOLUTION BREAKDOWN")
        print("-" * 60)
        for rtype, data in sorted(breakdown.items()):
            pct = (data["count"] / total * 100) if total > 0 else 0
            print("  {:<12} {:>6} requests ({:5.1f}%)  ${:.6f}  avg {:.0f}ms".format(
                rtype, data["count"], pct, data["cost"], data["avg_latency_ms"]
            ))
        print()

        if top_cache:
            print("-" * 60)
            print("  TOP CACHED PROMPTS")
            print("-" * 60)
            for entry in top_cache:
                prompt_preview = (entry["prompt_text"] or "")[:50]
                if len(entry["prompt_text"] or "") > 50:
                    prompt_preview += "..."
                print("  [{} hits] {}".format(entry["hit_count"], prompt_preview))
            print()

        if top_rules:
            print("-" * 60)
            print("  TOP RULE MATCHES")
            print("-" * 60)
            for entry in top_rules:
                print("  [{} hits] model={}".format(entry["hits"], entry["model"]))
            print()

        print("=" * 60)

    except sqlite3.OperationalError as e:
        print("Database error: {}".format(e))
        print("The database may not have the expected schema.")
    finally:
        conn.close()


if __name__ == "__main__":
    analyze()
