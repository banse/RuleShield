"""Test monitor routes: /api/test-monitor/*.

Contains endpoints for starting/stopping test runs, listing scripts,
viewing run events, and RuleShield snapshots per test run.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from ruleshield import state
from ruleshield.state import (
    TEST_MONITOR_LOCK,
    TEST_RUNS,
    TEST_LAST_RUN_BY_SCRIPT,
    TestRunState,
)

logger = logging.getLogger("ruleshield.proxy")

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

_DEFAULT_TEST_MODEL_PROFILES: list[dict[str, str]] = [
    {
        "id": "gpt5_mini_openai",
        "label": "GPT-5.1 Mini (OpenAI OAuth)",
        "provider": "openai_oauth",
        "provider_label": "OpenAI OAuth",
        "model": "gpt-5.1-codex-mini",
        "fallback_model": "gpt-4.1-mini",
        "script_suffix": "gpt5_mini_openai",
    },
    {
        "id": "gpt5_max_openai",
        "label": "GPT-5.1 Max (OpenAI OAuth)",
        "provider": "openai_oauth",
        "provider_label": "OpenAI OAuth",
        "model": "gpt-5.1-codex-max",
        "fallback_model": "gpt-5.1-codex-mini",
        "script_suffix": "gpt5_max_openai",
    },
    {
        "id": "gpt41_mini_openai",
        "label": "GPT-4.1 Mini (OpenAI OAuth)",
        "provider": "openai_oauth",
        "provider_label": "OpenAI OAuth",
        "model": "gpt-4.1-mini",
        "fallback_model": "gpt-5.1-codex-mini",
        "script_suffix": "gpt41_mini_openai",
    },
    {
        "id": "openrouter_arcee_trinity_free",
        "label": "Arcee Trinity Large (OpenRouter Free)",
        "provider": "openrouter",
        "provider_label": "OpenRouter",
        "model": "arcee-ai/trinity-large-preview:free",
        "fallback_model": "stepfun/step-3.5-flash:free",
        "script_suffix": "openrouter_arcee_trinity_free",
    },
    {
        "id": "openrouter_stepfun_flash_free",
        "label": "StepFun 3.5 Flash (OpenRouter Free)",
        "provider": "openrouter",
        "provider_label": "OpenRouter",
        "model": "stepfun/step-3.5-flash:free",
        "fallback_model": "arcee-ai/trinity-large-preview:free",
        "script_suffix": "openrouter_stepfun_flash_free",
    },
]

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MODEL_PROFILES_PATH = (
    _PROJECT_ROOT / "ruleshield" / "training_configs" / "model_profiles.yaml"
)

_RUN_DIR_PATTERN = re.compile(r"Run directory:\s*(.+)$")
_SHADOW_FINAL_PATTERN = re.compile(r"shadow:\s*(.+shadow-final\.json)\s*$")


def _test_roots() -> list[Path]:
    cwd = Path.cwd()
    roots = [cwd / "tests", cwd / "demo"]
    return [root for root in roots if root.exists() and root.is_dir()]


def _discover_test_scripts() -> list[dict[str, str]]:
    scripts: list[dict[str, str]] = []
    for root in _test_roots():
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file():
                continue
            name = file_path.name
            if file_path.suffix == ".sh" and name.startswith("test_"):
                script_type = "shell"
            elif file_path.suffix == ".py" and name.startswith("test_"):
                script_type = "pytest"
            else:
                continue
            scripts.append(
                {
                    "path": str(file_path.resolve()),
                    "name": name,
                    "type": script_type,
                }
            )
    return scripts


def _extract_run_directory_from_events(
    events: list[dict[str, Any]],
) -> Path | None:
    for event in events:
        text = str(event.get("text") or "").strip()
        if not text:
            continue
        run_match = _RUN_DIR_PATTERN.search(text)
        if run_match:
            candidate = Path(run_match.group(1).strip()).expanduser()
            if candidate.exists():
                return candidate
        shadow_match = _SHADOW_FINAL_PATTERN.search(text)
        if shadow_match:
            shadow_file = Path(shadow_match.group(1).strip()).expanduser()
            if shadow_file.exists():
                return shadow_file.parent
    return None


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _safe_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except Exception:
        return 0.0


def _parse_request_created_at(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _count_resolution_types(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        key = str(entry.get("resolution_type") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _count_confidence_directions(
    events: list[dict[str, Any]],
) -> tuple[int, int]:
    up = 0
    down = 0
    for event in events:
        if str(event.get("event_type", "")) != "confidence_update":
            continue
        details = (
            event.get("details")
            if isinstance(event.get("details"), dict)
            else {}
        )
        direction = str(
            details.get("direction", event.get("direction", ""))
        ).lower()
        if direction == "up":
            up += 1
        elif direction == "down":
            down += 1
    return up, down


def _build_test_command(script_path: Path, script_type: str) -> list[str]:
    if script_type == "shell":
        return ["bash", str(script_path)]
    python_bin = Path.cwd() / ".venv" / "bin" / "python"
    if not python_bin.exists():
        python_bin = Path("/usr/bin/env")
        return [
            str(python_bin),
            "python3",
            "-m",
            "pytest",
            str(script_path),
            "-q",
        ]
    return [str(python_bin), "-m", "pytest", str(script_path), "-q"]


def _model_profiles() -> list[dict[str, str]]:
    required_fields = {
        "id",
        "label",
        "provider",
        "provider_label",
        "model",
        "fallback_model",
        "script_suffix",
    }

    if not _MODEL_PROFILES_PATH.is_file():
        return list(_DEFAULT_TEST_MODEL_PROFILES)

    try:
        raw = (
            yaml.safe_load(
                _MODEL_PROFILES_PATH.read_text(encoding="utf-8")
            )
            or {}
        )
    except Exception as exc:
        logger.warning(
            "Could not read model profiles file %s: %s",
            _MODEL_PROFILES_PATH,
            exc,
        )
        return list(_DEFAULT_TEST_MODEL_PROFILES)

    profiles = raw.get("profiles", [])
    if not isinstance(profiles, list):
        logger.warning(
            "Invalid model profiles format in %s: 'profiles' must be a list",
            _MODEL_PROFILES_PATH,
        )
        return list(_DEFAULT_TEST_MODEL_PROFILES)

    normalized: list[dict[str, str]] = []
    for entry in profiles:
        if not isinstance(entry, dict):
            continue
        missing = [
            field for field in required_fields if not entry.get(field)
        ]
        if missing:
            logger.warning(
                "Skipping invalid model profile in %s (missing: %s)",
                _MODEL_PROFILES_PATH,
                ", ".join(sorted(missing)),
            )
            continue
        normalized.append(
            {field: str(entry[field]) for field in required_fields}
        )

    if not normalized:
        logger.warning(
            "No valid model profiles found in %s; using defaults",
            _MODEL_PROFILES_PATH,
        )
        return list(_DEFAULT_TEST_MODEL_PROFILES)

    return normalized


def _profile_by_id(profile_id: str | None) -> dict[str, str]:
    profile_map = {
        profile["id"]: profile for profile in _model_profiles()
    }
    if profile_id and profile_id in profile_map:
        return profile_map[profile_id]
    return _model_profiles()[0]


def _resolve_profile_script_path(
    script_file: Path, profile: dict[str, str]
) -> Path:
    if script_file.suffix != ".sh":
        return script_file
    variant = script_file.with_name(
        f"{script_file.stem}.{profile['script_suffix']}{script_file.suffix}"
    )
    if variant.is_file():
        return variant
    return script_file


def _status_from_run(run: TestRunState | None) -> str:
    if run is None:
        return "not_started"
    return run.status


def _append_test_event(run: TestRunState, kind: str, text: str):
    run.events.append(
        {
            "ts": time.time(),
            "kind": kind,
            "text": text.rstrip(),
        }
    )
    if len(run.events) > 1200:
        run.events = run.events[-1200:]


async def _stream_test_output(run: TestRunState):
    proc = run.process
    if proc is None or proc.stdout is None:
        return
    while True:
        raw_line = await proc.stdout.readline()
        if not raw_line:
            break
        line = raw_line.decode(errors="replace").rstrip("\n")
        async with TEST_MONITOR_LOCK:
            _append_test_event(run, "output", line)


async def _wait_test_run(run: TestRunState):
    proc = run.process
    if proc is None:
        return
    return_code = await proc.wait()
    async with TEST_MONITOR_LOCK:
        run.return_code = return_code
        run.ended_at = time.time()
        if return_code == 0:
            run.status = "inactive"
        else:
            run.status = "failed"
        _append_test_event(
            run,
            "output",
            f"[process exited] code={return_code} status={run.status}",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/api/test-monitor/scripts")
async def api_test_monitor_scripts():
    """List all test scripts and their current status."""
    try:
        discovered = _discover_test_scripts()
        script_map = {entry["path"]: entry for entry in discovered}

        async with TEST_MONITOR_LOCK:
            scripts = []
            for path, entry in sorted(
                script_map.items(), key=lambda item: item[1]["name"]
            ):
                last_run_id = TEST_LAST_RUN_BY_SCRIPT.get(path)
                last_run = (
                    TEST_RUNS.get(last_run_id) if last_run_id else None
                )
                scripts.append(
                    {
                        "path": path,
                        "name": entry["name"],
                        "type": entry["type"],
                        "default_model_profile_id": _model_profiles()[0][
                            "id"
                        ],
                        "status": _status_from_run(last_run),
                        "active_run_id": (
                            last_run.run_id
                            if last_run and last_run.status == "active"
                            else None
                        ),
                        "last_run_id": (
                            last_run.run_id if last_run else None
                        ),
                        "last_return_code": (
                            last_run.return_code if last_run else None
                        ),
                        "last_started_at": (
                            last_run.started_at if last_run else None
                        ),
                        "last_ended_at": (
                            last_run.ended_at if last_run else None
                        ),
                    }
                )
            active_count = sum(
                1
                for run in TEST_RUNS.values()
                if run.status == "active"
            )
            return {
                "scripts": scripts,
                "active_runs": active_count,
                "total": len(scripts),
            }
    except Exception as exc:
        logger.error(
            "Failed to fetch /api/test-monitor/scripts: %s", exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.get("/api/test-monitor/model-profiles")
async def api_test_monitor_model_profiles():
    """List available model/provider profiles for test runs."""
    try:
        profiles = _model_profiles()
        return {
            "profiles": profiles,
            "default_profile_id": profiles[0]["id"] if profiles else "",
        }
    except Exception as exc:
        logger.error(
            "Failed to fetch /api/test-monitor/model-profiles: %s", exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.get("/api/test-monitor/runs")
async def api_test_monitor_runs(
    limit: int = Query(default=40, ge=1, le=200),
):
    """List recent runs across all test scripts."""
    try:
        async with TEST_MONITOR_LOCK:
            runs = sorted(
                TEST_RUNS.values(),
                key=lambda run: run.started_at,
                reverse=True,
            )[:limit]
            out = [
                {
                    "run_id": run.run_id,
                    "script_path": run.script_path,
                    "command": run.command,
                    "status": run.status,
                    "started_at": run.started_at,
                    "ended_at": run.ended_at,
                    "return_code": run.return_code,
                    "event_count": len(run.events),
                    "model_profile_id": run.model_profile_id,
                    "model": run.model,
                    "provider_label": run.provider_label,
                }
                for run in runs
            ]
        return {"runs": out, "limit": limit}
    except Exception as exc:
        logger.error(
            "Failed to fetch /api/test-monitor/runs: %s", exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.get("/api/test-monitor/runs/{run_id}/events")
async def api_test_monitor_run_events(
    run_id: str,
    limit: int = Query(default=500, ge=20, le=2000),
):
    """Return monitor events for one run."""
    try:
        async with TEST_MONITOR_LOCK:
            run = TEST_RUNS.get(run_id)
            if run is None:
                return {
                    "run_id": run_id,
                    "status": "not_found",
                    "events": [],
                }
            events = run.events[-limit:]
            return {
                "run_id": run_id,
                "status": run.status,
                "events": events,
            }
    except Exception as exc:
        logger.error(
            "Failed to fetch /api/test-monitor/runs/%s/events: %s",
            run_id,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.get("/api/test-monitor/runs/{run_id}/ruleshield")
async def api_test_monitor_run_ruleshield(run_id: str):
    """Run-specific RuleShield snapshot using existing prompt-training summaries."""
    # Import the API functions we need for live preview
    from ruleshield.routes.api_routes import (
        api_stats,
        api_shadow,
        api_requests,
        api_rule_events,
    )

    try:
        async with TEST_MONITOR_LOCK:
            run = TEST_RUNS.get(run_id)
            if run is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Run '{run_id}' not found"},
                )
            run_dir = _extract_run_directory_from_events(run.events)

        started_at_dt = datetime.fromtimestamp(
            run.started_at, tz=timezone.utc
        )

        async def _build_live_preview(
            run_dir_value: str,
        ) -> dict[str, Any]:
            stats_snapshot = await api_stats()
            stats_payload = (
                stats_snapshot
                if isinstance(stats_snapshot, dict)
                else {}
            )
            shadow_snapshot = await api_shadow(recent=None, rule_id=None)
            shadow_payload = (
                shadow_snapshot
                if isinstance(shadow_snapshot, dict)
                else {}
            )
            requests_payload = await api_requests(limit=300)
            requests_list = (
                requests_payload.get("requests", [])
                if isinstance(requests_payload, dict)
                else []
            )
            rule_events_payload = await api_rule_events(limit=500)
            rule_events_list = (
                rule_events_payload.get("events", [])
                if isinstance(rule_events_payload, dict)
                and isinstance(
                    rule_events_payload.get("events"), list
                )
                else []
            )

            recent_requests = [
                entry
                for entry in requests_list
                if isinstance(entry, dict)
                and (
                    _parse_request_created_at(entry.get("created_at"))
                    or datetime.min.replace(tzinfo=timezone.utc)
                )
                >= started_at_dt
            ]
            request_breakdown = _count_resolution_types(recent_requests)

            recent_rule_events = [
                event
                for event in rule_events_list
                if isinstance(event, dict)
                and (
                    _parse_request_created_at(event.get("created_at"))
                    or datetime.min.replace(tzinfo=timezone.utc)
                )
                >= started_at_dt
            ]
            recent_rule_events = sorted(
                recent_rule_events,
                key=lambda item: str(item.get("created_at", "")),
                reverse=True,
            )[:12]

            conf_up_total, conf_down_total = _count_confidence_directions(
                rule_events_list
            )
            confidence_up = max(
                0, conf_up_total - int(run.baseline_confidence_up)
            )
            confidence_down = max(
                0, conf_down_total - int(run.baseline_confidence_down)
            )

            current_rule_hits = int(
                _safe_number(stats_payload.get("rule_hits", 0))
            )
            current_cache_hits = int(
                _safe_number(stats_payload.get("cache_hits", 0))
            )
            current_shadow_total = int(
                _safe_number(
                    shadow_payload.get("total_comparisons", 0)
                )
            )
            current_cost_without = float(
                _safe_number(stats_payload.get("cost_without", 0.0))
            )
            current_cost_with = float(
                _safe_number(stats_payload.get("cost_with", 0.0))
            )

            triggered_rules = max(
                int(request_breakdown.get("rule", 0)),
                max(
                    0,
                    current_rule_hits - int(run.baseline_rule_hits),
                ),
            )
            triggered_cache = max(
                int(request_breakdown.get("cache", 0)),
                max(
                    0,
                    current_cache_hits - int(run.baseline_cache_hits),
                ),
            )
            would_trigger_shadow = max(
                0,
                current_shadow_total
                - int(run.baseline_shadow_total),
            )
            cost_without = max(
                0.0,
                current_cost_without
                - float(run.baseline_cost_without),
            )
            cost_with = max(
                0.0,
                current_cost_with - float(run.baseline_cost_with),
            )
            savings_usd = max(0.0, cost_without - cost_with)
            savings_pct = (
                (savings_usd / cost_without * 100.0)
                if cost_without > 0
                else 0.0
            )

            return {
                "run_id": run_id,
                "status": run.status,
                "available": True,
                "source": "live_preview",
                "run_dir": run_dir_value,
                "request_breakdown": request_breakdown,
                "triggered_rules": triggered_rules,
                "triggered_cache": triggered_cache,
                "would_trigger_shadow": would_trigger_shadow,
                "cost_without": round(cost_without, 6),
                "cost_with": round(cost_with, 6),
                "savings_usd": round(savings_usd, 6),
                "savings_pct": round(savings_pct, 2),
                "shadow_enabled": bool(
                    shadow_payload.get(
                        "enabled", state.settings.shadow_mode
                    )
                ),
                "confidence_up": confidence_up,
                "confidence_down": confidence_down,
                "recent_rule_events": recent_rule_events,
            }

        if run_dir is None:
            return await _build_live_preview("")

        summary_paths = sorted(run_dir.rglob("ruleshield-summary.json"))
        if not summary_paths:
            return await _build_live_preview(str(run_dir))

        summaries = [_read_json_file(path) for path in summary_paths]
        summaries = [entry for entry in summaries if entry]
        if not summaries:
            return {
                "run_id": run_id,
                "status": run.status,
                "available": False,
                "run_dir": str(run_dir),
                "reason": "invalid_summary_files",
            }

        request_breakdown: dict[str, int] = {}
        recent_rule_events: list[dict[str, Any]] = []
        confidence_up = 0
        confidence_down = 0

        for entry in summaries:
            rs = (
                entry.get("ruleshield_summary", {})
                if isinstance(entry.get("ruleshield_summary"), dict)
                else {}
            )
            if not isinstance(rs, dict):
                continue
            breakdown = rs.get("request_breakdown", {})
            if isinstance(breakdown, dict):
                for key, value in breakdown.items():
                    try:
                        request_breakdown[key] = (
                            request_breakdown.get(key, 0) + int(value)
                        )
                    except Exception:
                        continue
            events = rs.get("recent_rule_events", [])
            if isinstance(events, list):
                recent_rule_events.extend(
                    [
                        event
                        for event in events
                        if isinstance(event, dict)
                    ]
                )

        recent_rule_events_sorted = sorted(
            recent_rule_events,
            key=lambda item: str(item.get("created_at", "")),
            reverse=True,
        )
        confidence_events = [
            event
            for event in recent_rule_events_sorted
            if event.get("event_type") == "confidence_update"
        ]
        for event in confidence_events:
            direction = str(
                (event.get("details") or {}).get(
                    "direction", event.get("direction", "")
                )
            ).lower()
            if direction == "up":
                confidence_up += 1
            elif direction == "down":
                confidence_down += 1

        first = summaries[0]
        last = summaries[-1]
        first_rs = (
            first.get("ruleshield_summary", {})
            if isinstance(first.get("ruleshield_summary"), dict)
            else {}
        )
        last_rs = (
            last.get("ruleshield_summary", {})
            if isinstance(last.get("ruleshield_summary"), dict)
            else {}
        )
        first_stats = (
            first_rs.get("stats_snapshot", {})
            if isinstance(first_rs.get("stats_snapshot"), dict)
            else {}
        )
        last_stats = (
            last_rs.get("stats_snapshot", {})
            if isinstance(last_rs.get("stats_snapshot"), dict)
            else {}
        )
        first_shadow = (
            first_rs.get("shadow_snapshot", {})
            if isinstance(first_rs.get("shadow_snapshot"), dict)
            else {}
        )
        last_shadow = (
            last_rs.get("shadow_snapshot", {})
            if isinstance(last_rs.get("shadow_snapshot"), dict)
            else {}
        )

        if len(summaries) == 1:
            first_stats = {
                "rule_hits": int(run.baseline_rule_hits),
                "cache_hits": int(run.baseline_cache_hits),
                "cost_without": float(run.baseline_cost_without),
                "cost_with": float(run.baseline_cost_with),
            }
            first_shadow = {
                "total_comparisons": int(run.baseline_shadow_total),
            }

        rule_hits_delta = max(
            0.0,
            _safe_number(last_stats.get("rule_hits"))
            - _safe_number(first_stats.get("rule_hits")),
        )
        cache_hits_delta = max(
            0.0,
            _safe_number(last_stats.get("cache_hits"))
            - _safe_number(first_stats.get("cache_hits")),
        )
        shadow_comparisons_delta = max(
            0.0,
            _safe_number(last_shadow.get("total_comparisons"))
            - _safe_number(first_shadow.get("total_comparisons")),
        )
        cost_without_delta = max(
            0.0,
            _safe_number(last_stats.get("cost_without"))
            - _safe_number(first_stats.get("cost_without")),
        )
        cost_with_delta = max(
            0.0,
            _safe_number(last_stats.get("cost_with"))
            - _safe_number(first_stats.get("cost_with")),
        )

        if len(summaries) == 1:
            rule_hits_delta = float(
                int(request_breakdown.get("rule", 0))
            )
            cache_hits_delta = float(
                int(request_breakdown.get("cache", 0))
            )
            shadow_comparisons_delta = float(
                int(request_breakdown.get("shadow", 0))
            )
            cost_without_delta = 0.0
            cost_with_delta = 0.0
        savings_delta = max(
            0.0, cost_without_delta - cost_with_delta
        )
        savings_pct = (
            (savings_delta / cost_without_delta * 100.0)
            if cost_without_delta > 0
            else 0.0
        )

        return {
            "run_id": run_id,
            "status": run.status,
            "available": True,
            "run_dir": str(run_dir),
            "summary_files": [str(path) for path in summary_paths],
            "request_breakdown": request_breakdown,
            "triggered_rules": int(rule_hits_delta),
            "triggered_cache": int(cache_hits_delta),
            "would_trigger_shadow": int(shadow_comparisons_delta),
            "cost_without": round(cost_without_delta, 6),
            "cost_with": round(cost_with_delta, 6),
            "savings_usd": round(savings_delta, 6),
            "savings_pct": round(savings_pct, 2),
            "shadow_enabled": bool(
                last_shadow.get("enabled", False)
            ),
            "confidence_up": confidence_up,
            "confidence_down": confidence_down,
            "recent_rule_events": recent_rule_events_sorted[:12],
            "source": "ruleshield-summary",
        }
    except Exception as exc:
        logger.error(
            "Failed to fetch /api/test-monitor/runs/%s/ruleshield: %s",
            run_id,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/test-monitor/start")
async def api_test_monitor_start(request: Request):
    """Start a test script from the monitored test directories."""
    # Import for baseline snapshots
    from ruleshield.routes.api_routes import (
        api_stats,
        api_shadow,
        api_rule_events,
    )

    try:
        body = await request.json()
        script_path = str(body.get("script_path", "")).strip()
        model_profile_id = (
            str(body.get("model_profile_id", "")).strip() or None
        )
        if not script_path:
            return JSONResponse(
                status_code=400,
                content={"error": "script_path is required"},
            )

        discovered = _discover_test_scripts()
        script_by_path = {
            entry["path"]: entry for entry in discovered
        }
        entry = script_by_path.get(script_path)
        if entry is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Script not found in monitored test directories"
                },
            )

        profile = _profile_by_id(model_profile_id)
        script_file = Path(script_path)
        resolved_script = _resolve_profile_script_path(
            script_file, profile
        )
        command = _build_test_command(resolved_script, entry["type"])
        run_id = (
            f"run-{int(time.time())}-{random.randint(1000, 9999)}"
        )

        async with TEST_MONITOR_LOCK:
            last_run_id = TEST_LAST_RUN_BY_SCRIPT.get(script_path)
            last_run = (
                TEST_RUNS.get(last_run_id) if last_run_id else None
            )
            if last_run and last_run.status == "active":
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": "Script is already active",
                        "run_id": last_run.run_id,
                    },
                )

        child_env = os.environ.copy()
        child_env["PYTHONUNBUFFERED"] = "1"
        child_env.setdefault("PYTHONIOENCODING", "utf-8")
        child_env["MODEL"] = profile["model"]
        child_env["FALLBACK_MODEL"] = profile["fallback_model"]
        child_env["RULESHIELD_TEST_PROVIDER"] = profile["provider"]
        child_env["RULESHIELD_TEST_PROFILE_ID"] = profile["id"]
        child_env["RULESHIELD_TEST_MONITOR"] = "1"
        child_env["AUTO_GATEWAY_RESTART"] = "0"

        stats_snapshot = await api_stats()
        stats_payload = (
            stats_snapshot
            if isinstance(stats_snapshot, dict)
            else {}
        )
        shadow_snapshot = await api_shadow(recent=None, rule_id=None)
        shadow_payload = (
            shadow_snapshot
            if isinstance(shadow_snapshot, dict)
            else {}
        )
        events_snapshot = await api_rule_events(limit=500)
        events_payload = (
            events_snapshot
            if isinstance(events_snapshot, dict)
            else {}
        )
        baseline_events = (
            events_payload.get("events", [])
            if isinstance(events_payload.get("events"), list)
            else []
        )
        baseline_conf_up, baseline_conf_down = (
            _count_confidence_directions(baseline_events)
        )

        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(Path.cwd()),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=child_env,
        )

        run = TestRunState(
            run_id=run_id,
            script_path=script_path,
            command=command,
            process=proc,
            model_profile_id=profile["id"],
            model=profile["model"],
            provider_label=profile["provider_label"],
            baseline_shadow_total=int(
                _safe_number(
                    shadow_payload.get("total_comparisons", 0)
                )
            ),
            baseline_rule_hits=int(
                _safe_number(stats_payload.get("rule_hits", 0))
            ),
            baseline_cache_hits=int(
                _safe_number(stats_payload.get("cache_hits", 0))
            ),
            baseline_cost_without=float(
                _safe_number(
                    stats_payload.get("cost_without", 0.0)
                )
            ),
            baseline_cost_with=float(
                _safe_number(stats_payload.get("cost_with", 0.0))
            ),
            baseline_confidence_up=baseline_conf_up,
            baseline_confidence_down=baseline_conf_down,
        )
        _append_test_event(run, "input", f"$ {' '.join(command)}")
        _append_test_event(
            run,
            "input",
            (
                f"[profile] id={profile['id']} provider={profile['provider_label']} "
                f"model={profile['model']} fallback={profile['fallback_model']}"
            ),
        )

        async with TEST_MONITOR_LOCK:
            TEST_RUNS[run_id] = run
            TEST_LAST_RUN_BY_SCRIPT[script_path] = run_id

        asyncio.create_task(_stream_test_output(run))
        asyncio.create_task(_wait_test_run(run))

        return {
            "started": True,
            "run_id": run_id,
            "script_path": script_path,
            "resolved_script_path": str(resolved_script),
            "status": "active",
            "command": command,
            "model_profile_id": profile["id"],
            "model": profile["model"],
            "provider_label": profile["provider_label"],
        }
    except Exception as exc:
        logger.error("Failed to start test monitor run: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/test-monitor/stop")
async def api_test_monitor_stop(request: Request):
    """Stop/abort an active test run."""
    try:
        body = await request.json()
        run_id = str(body.get("run_id", "")).strip()
        if not run_id:
            return JSONResponse(
                status_code=400,
                content={"error": "run_id is required"},
            )

        proc: asyncio.subprocess.Process | None = None
        async with TEST_MONITOR_LOCK:
            run = TEST_RUNS.get(run_id)
            if run is None:
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Run '{run_id}' not found"},
                )
            if run.status != "active":
                return {
                    "stopped": False,
                    "run_id": run_id,
                    "status": run.status,
                }
            run.stop_requested = True
            _append_test_event(run, "input", "[stop requested]")
            proc = run.process

        if proc is not None and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except TimeoutError:
                proc.kill()
                await proc.wait()

        async with TEST_MONITOR_LOCK:
            run = TEST_RUNS.get(run_id)
            status = run.status if run else "failed"
            return {
                "stopped": True,
                "run_id": run_id,
                "status": status,
            }
    except Exception as exc:
        logger.error("Failed to stop test monitor run: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )
