"""Dashboard API routes: /health, /api/stats, /api/requests, /api/rules, etc.

Contains health check, statistics, request history, rule management,
shadow mode, feedback, and runtime config endpoints.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from ruleshield import state
from ruleshield.helpers import (
    persist_runtime_settings,
    to_bool,
    wrap_openai_response,
)
from ruleshield.router import SmartRouter

logger = logging.getLogger("ruleshield.proxy")

router = APIRouter()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health")
async def health():
    """Liveness check."""
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


@router.get("/api/stats")
async def api_stats():
    """Aggregated statistics for the dashboard."""
    try:
        cache_stats = await state.cache_manager.get_stats()
        rule_stats = state.rule_engine.get_stats()

        total_requests = cache_stats.get("total_requests", 0)
        cache_hits = cache_stats.get("cache_hits", 0)
        rule_hits = cache_stats.get("rule_hits", 0)
        routed_calls = cache_stats.get("routed_calls", 0)
        llm_calls = cache_stats.get("llm_calls", 0)
        passthrough_calls = cache_stats.get("passthrough_calls", 0)

        if routed_calls == 0 and total_requests > 0:
            routed_calls = max(
                0,
                total_requests
                - cache_hits
                - rule_hits
                - passthrough_calls
                - llm_calls,
            )

        dashboard = state.metrics.dashboard
        cost_without = dashboard.total_cost_without
        cost_with = dashboard.total_cost_with

        if cost_without == 0 and cache_stats.get("total_savings", 0) > 0:
            cost_without = cache_stats["total_savings"]
            cost_with = 0.0

        savings_usd = cost_without - cost_with
        savings_pct = (
            (savings_usd / cost_without * 100) if cost_without > 0 else 0.0
        )

        uptime_seconds = time.monotonic() - state.proxy_start_time

        return {
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "rule_hits": rule_hits,
            "routed_calls": routed_calls,
            "passthrough_calls": passthrough_calls,
            "llm_calls": llm_calls,
            "cost_without": round(cost_without, 4),
            "cost_with": round(cost_with, 4),
            "savings_usd": round(savings_usd, 4),
            "savings_pct": round(savings_pct, 1),
            "uptime_seconds": round(uptime_seconds),
        }
    except Exception as exc:
        logger.error("Failed to compute /api/stats: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


@router.get("/api/requests")
async def api_requests(limit: int = Query(default=20, ge=1, le=200)):
    """Recent requests for the dashboard."""
    try:
        recent = await state.cache_manager.get_recent_requests(limit=limit)

        requests_out = []
        for entry in recent:
            requests_out.append(
                {
                    "id": entry.get("id"),
                    "prompt": (entry.get("prompt_text") or "")[:200],
                    "resolution_type": entry.get("resolution_type", "unknown"),
                    "model": entry.get("model", "unknown"),
                    "cost": entry.get("cost_usd", 0.0),
                    "tokens_in": entry.get("tokens_in", 0),
                    "tokens_out": entry.get("tokens_out", 0),
                    "latency_ms": entry.get("latency_ms", 0),
                    "created_at": entry.get("created_at", ""),
                }
            )

        return {"requests": requests_out}
    except Exception as exc:
        logger.error("Failed to fetch /api/requests: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@router.get("/api/rules")
async def api_rules():
    """All rules and statistics for the dashboard."""
    try:
        stats = state.rule_engine.get_stats()

        rules_out = []
        for r in state.rule_engine.rules:
            confidence = r.get("confidence", 1.0)
            if confidence >= 0.9:
                confidence_level = "CONFIRMED"
            elif confidence >= 0.7:
                confidence_level = "LIKELY"
            else:
                confidence_level = "POSSIBLE"

            deployment = r.get("deployment", "production")
            enabled = r.get("enabled", True)
            if not enabled:
                status = "paused"
            elif deployment == "candidate":
                status = "candidate"
            else:
                status = "live"

            rules_out.append(
                {
                    "id": r.get("id"),
                    "name": r.get("name", r.get("id", "")),
                    "hits": r.get("hit_count", 0),
                    "shadow_hits": r.get("shadow_hit_count", 0),
                    "confidence": r.get("confidence", 1.0),
                    "confidence_level": confidence_level,
                    "enabled": enabled,
                    "deployment": deployment,
                    "status": status,
                    "pattern_count": len(r.get("patterns", [])),
                }
            )

        return {
            "rules": rules_out,
            "total": stats.get("total_rules", len(rules_out)),
            "active": stats.get("active_rules", len(rules_out)),
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/rules: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/rules/{rule_id}/toggle")
async def api_toggle_rule(rule_id: str):
    """Toggle a rule's enabled state."""
    try:
        for rule in state.rule_engine.rules:
            if rule.get("id") == rule_id:
                new_state = not rule.get("enabled", True)
                rule["enabled"] = new_state
                state.rule_engine._dirty = True
                state.rule_engine._save_rules_to_disk()
                if state.feedback_manager is not None:
                    await state.feedback_manager.log_rule_event(
                        rule_id=rule_id,
                        event_type="rule_toggled",
                        direction="up" if new_state else "down",
                        old_confidence=float(rule.get("confidence", 1.0)),
                        new_confidence=float(rule.get("confidence", 1.0)),
                        delta=0.0,
                        details={"enabled": new_state},
                    )
                return {"id": rule_id, "enabled": new_state}

        return JSONResponse(
            status_code=404,
            content={"error": f"Rule '{rule_id}' not found"},
        )
    except Exception as exc:
        logger.error("Failed to toggle rule %s: %s", rule_id, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.get("/api/rules/{rule_id}/response")
async def get_rule_response(rule_id: str):
    """Direct API access to a promoted rule's cached response."""
    for rule in state.rule_engine.rules:
        if rule.get("id") == rule_id:
            content = rule.get("response", {}).get("content", "")
            return wrap_openai_response(content, model="ruleshield-promoted")

    return JSONResponse(
        status_code=404,
        content={"error": f"Rule '{rule_id}' not found"},
    )


# ---------------------------------------------------------------------------
# Runtime config
# ---------------------------------------------------------------------------


@router.get("/api/runtime-config")
async def api_runtime_config():
    """Minimal runtime config state for dashboard toggles."""
    try:
        return {
            "rules_enabled": bool(state.settings.rules_enabled),
            "shadow_mode": bool(state.settings.shadow_mode),
            "cache_enabled": bool(state.settings.cache_enabled),
            "router_enabled": bool(state.settings.router_enabled),
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/runtime-config: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/runtime-config")
async def api_update_runtime_config(request: Request):
    """Update minimal runtime config toggles and persist them locally."""
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            return JSONResponse(
                status_code=400, content={"error": "JSON object required"}
            )

        allowed_fields = (
            "rules_enabled",
            "shadow_mode",
            "cache_enabled",
            "router_enabled",
        )
        applied: dict[str, bool] = {}
        ignored: list[str] = []

        for field in allowed_fields:
            if field not in payload:
                continue
            converted = to_bool(payload.get(field))
            if converted is None:
                ignored.append(field)
                continue
            setattr(state.settings, field, converted)
            applied[field] = converted

        persisted = False
        if applied:
            persisted = persist_runtime_settings(applied)
            if "router_enabled" in applied:
                if applied["router_enabled"]:
                    state.smart_router = SmartRouter(
                        config=state.settings.router_config or None
                    )
                else:
                    state.smart_router = None

        return {
            "applied": applied,
            "ignored": ignored,
            "persisted": persisted,
            "config": {
                "rules_enabled": bool(state.settings.rules_enabled),
                "shadow_mode": bool(state.settings.shadow_mode),
                "cache_enabled": bool(state.settings.cache_enabled),
                "router_enabled": bool(state.settings.router_enabled),
            },
        }
    except Exception as exc:
        logger.error("Failed to update /api/runtime-config: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


# ---------------------------------------------------------------------------
# Shadow mode
# ---------------------------------------------------------------------------


@router.get("/api/shadow")
async def api_shadow(
    recent: int | None = Query(default=None, ge=1, le=500),
    rule_id: str | None = Query(default=None),
):
    """Shadow mode comparison statistics for the dashboard."""
    if not isinstance(recent, (int, type(None))):
        recent = None
    if not isinstance(rule_id, (str, type(None))):
        rule_id = None

    try:
        shadow_stats = await state.cache_manager.get_shadow_stats(
            limit=recent, rule_id=rule_id
        )
        tune_examples = await state.cache_manager.get_shadow_examples(
            limit=5,
            match_quality="poor",
            rule_id=rule_id,
        )

        by_rule = []
        for entry in shadow_stats.get("per_rule", []):
            avg_sim = entry.get("avg_similarity", 0.0)
            if avg_sim >= 0.8:
                quality = "good"
            elif avg_sim >= 0.4:
                quality = "partial"
            else:
                quality = "poor"

            by_rule.append(
                {
                    "rule_id": entry.get("rule_id", ""),
                    "comparisons": entry.get("total", 0),
                    "avg_similarity": avg_sim,
                    "avg_similarity_pct": round(avg_sim * 100, 1),
                    "good": entry.get("good", 0),
                    "partial": entry.get("partial", 0),
                    "poor": entry.get("poor", 0),
                    "quality": quality,
                }
            )

        entries = sorted(
            by_rule, key=lambda e: e["comparisons"], reverse=True
        )[:5]

        return {
            "enabled": state.settings.shadow_mode,
            "total_comparisons": shadow_stats.get("total_comparisons", 0),
            "avg_similarity": shadow_stats.get("avg_similarity", 0.0),
            "avg_similarity_pct": round(
                float(shadow_stats.get("avg_similarity", 0.0)) * 100, 1
            ),
            "rules_ready": len(
                shadow_stats.get("ready_for_activation", [])
            ),
            "recent": recent,
            "rule_id": rule_id,
            "entries": entries,
            "by_rule": by_rule,
            "tune_examples": tune_examples,
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/shadow: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


# ---------------------------------------------------------------------------
# Rule events & feedback
# ---------------------------------------------------------------------------


@router.get("/api/rule-events")
async def api_rule_events(limit: int = Query(default=100, ge=1, le=500)):
    """Recent rule-engine change events."""
    try:
        if state.feedback_manager is None:
            return {"events": [], "limit": limit}
        events = await state.feedback_manager.get_recent_rule_events(
            limit=limit
        )
        return {"events": events, "limit": limit}
    except Exception as exc:
        logger.error("Failed to fetch /api/rule-events: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.get("/api/feedback")
async def api_feedback(limit: int = Query(default=50, ge=1, le=300)):
    """Recent feedback entries and aggregated per-rule feedback stats."""
    try:
        if state.feedback_manager is None:
            return {"entries": [], "stats": [], "limit": limit}
        entries = await state.feedback_manager.get_recent_feedback(limit=limit)
        stats = await state.feedback_manager.get_feedback_stats()
        return {"entries": entries, "stats": stats, "limit": limit}
    except Exception as exc:
        logger.error("Failed to fetch /api/feedback: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )
