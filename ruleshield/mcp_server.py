#!/usr/bin/env python3
"""RuleShield MCP Server -- exposes cost optimization tools to Hermes Agent.

Run as: python -m ruleshield.mcp_server
Configure in ~/.hermes/config.yaml:
  mcp_servers:
    ruleshield:
      type: stdio
      command: python
      args: ["-m", "ruleshield.mcp_server"]

Pure stdlib implementation: json, sys, sqlite3 -- no async, no external deps.
"""

import hashlib
import json
import re
import sqlite3
import sys
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from ruleshield.cron_optimizer import (
    activate_cron_profile,
    analyze_recurring_workflows,
    execute_active_cron_profile,
    list_cron_profiles,
    load_cron_profile,
    suggest_cron_profile,
)
from ruleshield.cron_validation import run_cron_shadow

DB_PATH = Path.home() / ".ruleshield" / "cache.db"
RULES_DIR = Path.home() / ".ruleshield" / "rules"

# Approximate pricing (per token)
INPUT_COST_PER_TOKEN = 0.005 / 1000   # $0.005 per 1k input tokens
OUTPUT_COST_PER_TOKEN = 0.015 / 1000  # $0.015 per 1k output tokens
AVG_OUTPUT_RATIO = 1.5

_WORD_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "an", "the", "is", "it", "to", "of", "in", "on", "at",
    "and", "or", "but", "for", "i", "me", "my", "you", "your",
    "we", "do", "can", "this", "that", "what", "how",
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_db():
    """Return a sqlite3 connection or None if the DB does not exist."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _tokenize(text):
    return _WORD_RE.findall(text.lower())


def _first_n_words(text, n=5):
    words = _tokenize(text)
    return " ".join(words[:n])


def _word_overlap(a, b):
    words_a = set(_tokenize(a))
    words_b = set(_tokenize(b))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _get_stats():
    """Query request_log for aggregated cost savings statistics."""
    conn = _get_db()
    if conn is None:
        return {
            "error": None,
            "total_requests": 0,
            "cache_hits": 0,
            "rule_hits": 0,
            "routed": 0,
            "llm_calls": 0,
            "savings_pct": 0.0,
            "cost_without_ruleshield": 0.0,
            "cost_with_ruleshield": 0.0,
            "message": "No database found. RuleShield may not have processed any requests yet.",
        }

    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as cnt FROM request_log")
        total = cur.fetchone()["cnt"]

        if total == 0:
            conn.close()
            return {
                "total_requests": 0,
                "cache_hits": 0,
                "rule_hits": 0,
                "routed": 0,
                "llm_calls": 0,
                "savings_pct": 0.0,
                "cost_without_ruleshield": 0.0,
                "cost_with_ruleshield": 0.0,
                "message": "No requests logged yet.",
            }

        # Counts by resolution type
        cur.execute("""
            SELECT resolution_type, COUNT(*) as cnt, COALESCE(SUM(cost_usd), 0) as cost
            FROM request_log
            GROUP BY resolution_type
        """)
        rows = cur.fetchall()

        by_type = {}
        total_cost = 0.0
        for row in rows:
            rtype = row["resolution_type"] or "unknown"
            by_type[rtype] = {"count": row["cnt"], "cost": row["cost"]}
            total_cost += row["cost"]

        cache_hits = by_type.get("cache", {}).get("count", 0)
        rule_hits = by_type.get("rule", {}).get("count", 0)
        routed = by_type.get("routed", {}).get("count", 0)
        llm_calls = by_type.get("llm", {}).get("count", 0)

        # Savings estimate: cost that cache/rule hits saved
        saved_cost = (
            by_type.get("cache", {}).get("cost", 0)
            + by_type.get("rule", {}).get("cost", 0)
        )
        cost_without = total_cost + saved_cost
        cost_with = total_cost
        savings_pct = (saved_cost / cost_without * 100) if cost_without > 0 else 0.0

        conn.close()

        return {
            "total_requests": total,
            "cache_hits": cache_hits,
            "rule_hits": rule_hits,
            "routed": routed,
            "llm_calls": llm_calls,
            "savings_pct": round(savings_pct, 2),
            "cost_without_ruleshield": round(cost_without, 6),
            "cost_with_ruleshield": round(cost_with, 6),
        }

    except sqlite3.OperationalError as e:
        conn.close()
        return {"error": str(e), "message": "Database query failed."}


def _estimate_cost(prompt, model="unknown"):
    """Estimate cost of an LLM call and predict resolution."""
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    tokens_in = max(1, int(len(prompt.split()) * 1.3))
    tokens_out_est = int(tokens_in * AVG_OUTPUT_RATIO)

    cost_input = tokens_in * INPUT_COST_PER_TOKEN
    cost_output = tokens_out_est * OUTPUT_COST_PER_TOKEN
    estimated_cost = round(cost_input + cost_output, 6)

    # Check cache
    would_cache = False
    conn = _get_db()
    if conn is not None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM cache WHERE prompt_hash = ?", (prompt_hash,))
            would_cache = cur.fetchone() is not None
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    # Check rules
    would_rule = None
    if RULES_DIR.exists():
        text_lower = prompt.lower().strip()
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
                # Check conditions
                conds_ok = True
                for cond in rule.get("conditions", []):
                    if cond.get("type") == "max_length":
                        if len(text_lower) > cond.get("value", 9999):
                            conds_ok = False
                            break
                if not conds_ok:
                    continue
                # Check patterns
                for pat in rule.get("patterns", []):
                    ptype = pat.get("type", "")
                    pval = pat.get("value", "").lower()
                    matched = False
                    if ptype == "exact" and text_lower == pval:
                        matched = True
                    elif ptype == "contains" and pval in text_lower:
                        matched = True
                    elif ptype == "regex":
                        try:
                            if re.match(pval, text_lower):
                                matched = True
                        except re.error:
                            continue
                    if matched:
                        would_rule = rule.get("name", rule.get("id", "unknown"))
                        break
                if would_rule:
                    break
            if would_rule:
                break

    if would_cache:
        prediction = "cache"
        actual_cost = 0.0
    elif would_rule:
        prediction = "rule"
        actual_cost = 0.0
    else:
        prediction = "llm"
        actual_cost = estimated_cost

    return {
        "prompt_preview": prompt[:100] + ("..." if len(prompt) > 100 else ""),
        "estimated_tokens_in": tokens_in,
        "estimated_tokens_out": tokens_out_est,
        "estimated_cost_usd": estimated_cost,
        "would_cache_hit": would_cache,
        "would_rule_match": would_rule,
        "prediction": prediction,
        "predicted_cost_usd": actual_cost,
        "model": model,
    }


def _suggest_rules():
    """Analyze request_log and suggest new cost-saving rules."""
    conn = _get_db()
    if conn is None:
        return {"suggestions": [], "message": "No database found."}

    try:
        cur = conn.cursor()
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
        conn.close()

        if not rows:
            return {"suggestions": [], "message": "No LLM requests to analyze."}

        # Group by first 5 words
        groups = defaultdict(list)
        for row in rows:
            key = _first_n_words(row["prompt_text"])
            if key:
                groups[key].append({
                    "prompt": row["prompt_text"],
                    "response": row["response"] or "",
                })

        # Load existing patterns to skip duplicates
        existing = set()
        if RULES_DIR.exists():
            for f in RULES_DIR.glob("*.json"):
                try:
                    with open(f) as fh:
                        data = json.load(fh)
                        if not isinstance(data, list):
                            data = [data]
                        for rule in data:
                            for p in rule.get("patterns", []):
                                existing.add(p.get("value", "").lower())
                except (json.JSONDecodeError, IOError):
                    continue

        suggestions = []

        for key, entries in groups.items():
            if len(entries) < 3:
                continue

            # Check response consistency
            responses = [e["response"] for e in entries]
            overlaps = []
            for i in range(min(len(responses), 5)):
                for j in range(i + 1, min(len(responses), 5)):
                    overlaps.append(_word_overlap(responses[i], responses[j]))
            if not overlaps:
                continue

            avg_overlap = sum(overlaps) / len(overlaps)
            if avg_overlap < 0.5:
                continue

            canonical = Counter(responses).most_common(1)[0][0]

            # Extract keywords
            word_counts = Counter()
            for entry in entries:
                for w in set(_tokenize(entry["prompt"])):
                    if len(w) > 2 and w not in STOPWORDS:
                        word_counts[w] += 1

            threshold = len(entries) * 0.5
            keywords = [w for w, c in word_counts.most_common(10) if c >= threshold]
            new_keywords = [k for k in keywords if k not in existing]
            if not new_keywords and keywords:
                continue

            patterns = [
                {"type": "contains", "value": kw, "field": "last_user_message"}
                for kw in (new_keywords or keywords)[:5]
            ]
            if not patterns:
                continue

            max_len = max(len(e["prompt"]) for e in entries) + 10
            confidence = min(0.95, 0.5 + (avg_overlap * 0.3) + (len(entries) / 50))

            suggestions.append({
                "id": "suggested_{}".format(uuid.uuid4().hex[:8]),
                "name": "Suggested: {}".format(key),
                "description": "From {} similar requests (overlap: {:.0%})".format(
                    len(entries), avg_overlap
                ),
                "patterns": patterns,
                "conditions": [
                    {"type": "max_length", "value": max_len, "field": "last_user_message"},
                ],
                "response": {
                    "content": canonical[:500],
                    "model": "ruleshield-rule",
                },
                "confidence": round(confidence, 2),
                "priority": 5,
                "enabled": True,
                "hit_count": 0,
                "sample_count": len(entries),
            })

        return {
            "suggestions": suggestions,
            "count": len(suggestions),
            "message": "{} rule(s) suggested".format(len(suggestions)) if suggestions
                       else "No patterns found meeting threshold (3+ occurrences, 50%+ response overlap)",
        }

    except sqlite3.OperationalError as e:
        conn.close()
        return {"suggestions": [], "error": str(e)}


def _analyze_crons(min_occurrences=5, structured=True):
    """Find prompts occurring 5+ times -- candidates for direct API replacement."""
    return analyze_recurring_workflows(
        DB_PATH,
        min_occurrences=min_occurrences,
        structured=structured,
    )


def _suggest_cron_profile(prompt_hash_or_text, min_occurrences=3):
    """Create a draft cron optimization profile for a recurring prompt."""
    return suggest_cron_profile(
        DB_PATH,
        prompt_hash_or_text,
        min_occurrences=min_occurrences,
    )


def _list_cron_profiles():
    """List stored cron optimization profiles."""
    return list_cron_profiles()


def _show_cron_profile(profile_id):
    """Load a stored cron optimization profile."""
    return load_cron_profile(profile_id)


def _run_cron_shadow(profile_id, optimized_response="", sample_limit=3, payload_text="", model=None):
    """Run shadow validation for a stored cron optimization profile."""
    return run_cron_shadow(
        DB_PATH,
        profile_id,
        optimized_response,
        sample_limit=sample_limit,
        payload_text=payload_text,
        model=model,
    )


def _activate_cron_profile(profile_id, force=False):
    """Activate a validated cron optimization profile."""
    return activate_cron_profile(
        profile_id,
        db_path=DB_PATH,
        force=force,
    )


def _run_active_cron_profile(profile_id, payload_text, model=None):
    """Execute an active cron optimization profile."""
    return execute_active_cron_profile(
        profile_id,
        payload_text,
        model=model,
    )


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 request handler
# ---------------------------------------------------------------------------

def handle_request(request):
    """Handle a single JSON-RPC 2.0 request and return a response dict."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "ruleshield", "version": "1.0.0"},
            },
        }

    elif method == "notifications/initialized":
        return None  # No response for notifications

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "ruleshield_get_stats",
                        "description": "Get current RuleShield cost savings statistics",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "ruleshield_estimate_cost",
                        "description": "Estimate the cost of an LLM call before making it",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "prompt": {
                                    "type": "string",
                                    "description": "The prompt to estimate cost for",
                                },
                                "model": {
                                    "type": "string",
                                    "description": "Target model name",
                                },
                            },
                            "required": ["prompt"],
                        },
                    },
                    {
                        "name": "ruleshield_suggest_rules",
                        "description": "Suggest new cost-saving rules based on usage patterns",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "ruleshield_analyze_crons",
                        "description": (
                            "Identify recurring prompts that could be replaced "
                            "by direct API calls or rules"
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "min_occurrences": {
                                    "type": "integer",
                                    "description": "Minimum number of occurrences to flag",
                                    "default": 5,
                                },
                                "structured": {
                                    "type": "boolean",
                                    "description": "Return recurring workflow classification details",
                                    "default": True,
                                },
                            },
                        },
                    },
                    {
                        "name": "ruleshield_suggest_cron_profile",
                        "description": "Create a draft cron optimization profile from a recurring prompt",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "prompt_hash_or_text": {
                                    "type": "string",
                                    "description": "Prompt hash prefix or prompt text fragment",
                                },
                                "min_occurrences": {
                                    "type": "integer",
                                    "description": "Minimum number of occurrences required",
                                    "default": 3,
                                },
                            },
                            "required": ["prompt_hash_or_text"],
                        },
                    },
                    {
                        "name": "ruleshield_list_cron_profiles",
                        "description": "List stored draft and active cron optimization profiles",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "ruleshield_show_cron_profile",
                        "description": "Show a stored cron optimization profile by id",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "profile_id": {
                                    "type": "string",
                                    "description": "Cron profile id",
                                },
                            },
                            "required": ["profile_id"],
                        },
                    },
                    {
                        "name": "ruleshield_run_cron_shadow",
                        "description": "Run shadow validation for a cron optimization profile",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "profile_id": {
                                    "type": "string",
                                    "description": "Cron profile id",
                                },
                                "optimized_response": {
                                    "type": "string",
                                    "description": "Optimized output text to validate",
                                },
                                "payload_text": {
                                    "type": "string",
                                    "description": "Dynamic payload for automatic compact execution",
                                },
                                "model": {
                                    "type": "string",
                                    "description": "Optional compact execution model override",
                                },
                                "sample_limit": {
                                    "type": "integer",
                                    "description": "How many recent original runs to compare",
                                    "default": 3,
                                },
                            },
                            "required": ["profile_id"],
                        },
                    },
                    {
                        "name": "ruleshield_activate_cron_profile",
                        "description": "Activate a validated cron optimization profile",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "profile_id": {
                                    "type": "string",
                                    "description": "Cron profile id",
                                },
                                "force": {
                                    "type": "boolean",
                                    "description": "Force activation even if guardrails are not met",
                                    "default": False,
                                },
                            },
                            "required": ["profile_id"],
                        },
                    },
                    {
                        "name": "ruleshield_run_active_cron_profile",
                        "description": "Execute an active cron optimization profile with dynamic payload",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "profile_id": {
                                    "type": "string",
                                    "description": "Cron profile id",
                                },
                                "payload_text": {
                                    "type": "string",
                                    "description": "Dynamic payload text",
                                },
                                "model": {
                                    "type": "string",
                                    "description": "Optional execution model override",
                                },
                            },
                            "required": ["profile_id", "payload_text"],
                        },
                    },
                ],
            },
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name == "ruleshield_get_stats":
            result = _get_stats()
        elif tool_name == "ruleshield_estimate_cost":
            result = _estimate_cost(
                arguments.get("prompt", ""),
                arguments.get("model", "unknown"),
            )
        elif tool_name == "ruleshield_suggest_rules":
            result = _suggest_rules()
        elif tool_name == "ruleshield_analyze_crons":
            result = _analyze_crons(
                arguments.get("min_occurrences", 5),
                arguments.get("structured", True),
            )
        elif tool_name == "ruleshield_suggest_cron_profile":
            result = _suggest_cron_profile(
                arguments.get("prompt_hash_or_text", ""),
                arguments.get("min_occurrences", 3),
            )
        elif tool_name == "ruleshield_list_cron_profiles":
            result = _list_cron_profiles()
        elif tool_name == "ruleshield_show_cron_profile":
            result = _show_cron_profile(arguments.get("profile_id", ""))
        elif tool_name == "ruleshield_run_cron_shadow":
            result = _run_cron_shadow(
                arguments.get("profile_id", ""),
                arguments.get("optimized_response", ""),
                arguments.get("sample_limit", 3),
                arguments.get("payload_text", ""),
                arguments.get("model"),
            )
        elif tool_name == "ruleshield_activate_cron_profile":
            result = _activate_cron_profile(
                arguments.get("profile_id", ""),
                arguments.get("force", False),
            )
        elif tool_name == "ruleshield_run_active_cron_profile":
            result = _run_active_cron_profile(
                arguments.get("profile_id", ""),
                arguments.get("payload_text", ""),
                arguments.get("model"),
            )
        else:
            result = "Unknown tool: {}".format(tool_name)

        text_content = (
            json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
        )

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": text_content}],
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": "Unknown method: {}".format(method)},
    }


# ---------------------------------------------------------------------------
# Stdio transport
# ---------------------------------------------------------------------------

def main():
    """Read JSON-RPC from stdin line by line, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(e)},
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
