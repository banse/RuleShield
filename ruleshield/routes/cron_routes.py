"""Cron optimization profile routes: /api/cron-profiles/*.

Contains all CRUD endpoints for cron profiles, activation, execution,
shadow validation, and automation suggestions.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from ruleshield import state
from ruleshield.cron_automation import build_automation_suggestion
from ruleshield.cron_execution import get_profile_execution_history
from ruleshield.cron_optimizer import (
    activate_cron_profile,
    archive_cron_profile,
    delete_cron_profile,
    duplicate_cron_profile,
    execute_active_cron_profile,
    list_cron_profiles,
    load_cron_profile,
    restore_cron_profile,
    update_draft_cron_profile,
)
from ruleshield.cron_validation import get_profile_validation_history
from ruleshield.cron_validation import run_cron_shadow

logger = logging.getLogger("ruleshield.proxy")

router = APIRouter()


def _db_path() -> Path:
    """Resolve the cache DB path for cron operations."""
    if hasattr(state.cache_manager, "db_path"):
        return state.cache_manager.db_path
    return Path.home() / ".ruleshield" / "cache.db"


@router.get("/api/cron-profiles")
async def api_cron_profiles():
    """All cron optimization profiles and their runtime state."""
    try:
        result = list_cron_profiles()
        profiles = result.get("profiles", [])
        return {
            "profiles": profiles,
            "total": result.get("count", len(profiles)),
            "drafts": sum(
                1
                for profile in profiles
                if profile.get("status") == "draft"
            ),
            "active": sum(
                1
                for profile in profiles
                if profile.get("status") == "active"
            ),
            "ready": sum(
                1
                for profile in profiles
                if profile.get("runtime_status") == "ready"
            ),
        }
    except Exception as exc:
        logger.error("Failed to fetch /api/cron-profiles: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.get("/api/cron-profiles/{profile_id}")
async def api_cron_profile_detail(
    profile_id: str,
    history_limit: int = Query(default=8, ge=1, le=50),
):
    """Full cron profile document for dashboard detail views."""
    try:
        result = load_cron_profile(profile_id)
        profile = result.get("profile")
        if not profile:
            return JSONResponse(
                status_code=404,
                content={
                    "error": result.get(
                        "message",
                        f"Cron profile '{profile_id}' not found",
                    )
                },
            )
        return {
            "profile": profile,
            "path": result.get("path", ""),
            "history": get_profile_validation_history(
                _db_path(),
                profile_id,
                limit=history_limit,
            ),
            "execution_history": get_profile_execution_history(
                _db_path(),
                profile_id,
                limit=history_limit,
            ),
            "automation": (
                build_automation_suggestion(
                    profile,
                    cwd=Path.cwd(),
                )
                if profile.get("status") == "active"
                else None
            ),
        }
    except Exception as exc:
        logger.error(
            "Failed to fetch /api/cron-profiles/%s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/cron-profiles/{profile_id}/activate")
async def api_activate_cron_profile(profile_id: str, request: Request):
    """Activate a validated cron profile."""
    try:
        body = (
            await request.json()
            if request.headers.get("content-type", "").startswith(
                "application/json"
            )
            else {}
        )
        result = activate_cron_profile(
            profile_id,
            db_path=_db_path(),
            force=bool(body.get("force", False)),
        )
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": result.get("message", "Activation failed"),
                    "summary": result.get("summary"),
                },
            )
        return result
    except Exception as exc:
        logger.error(
            "Failed to activate cron profile %s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/cron-profiles/{profile_id}/execute")
async def api_execute_cron_profile(profile_id: str, request: Request):
    """Execute an active cron profile with a payload."""
    try:
        body = await request.json()
        result = execute_active_cron_profile(
            profile_id,
            str(body.get("payload_text", "")),
            db_path=_db_path(),
            model=body.get("model"),
        )
        if not result.get("execution"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": result.get("message", "Execution failed")
                },
            )
        return result
    except Exception as exc:
        logger.error(
            "Failed to execute cron profile %s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/cron-profiles/{profile_id}/shadow-run")
async def api_run_cron_profile_shadow(profile_id: str, request: Request):
    """Run shadow validation for a cron profile."""
    try:
        body = await request.json()
        result = run_cron_shadow(
            _db_path(),
            profile_id,
            optimized_response=str(body.get("optimized_response", "")),
            sample_limit=int(body.get("sample_limit", 3)),
            payload_text=str(body.get("payload_text", "")),
            model=body.get("model"),
        )
        if not result.get("count"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": result.get("message", "Shadow run failed")
                },
            )
        return result
    except Exception as exc:
        logger.error(
            "Failed to shadow-run cron profile %s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/cron-profiles/{profile_id}/update")
async def api_update_cron_profile(profile_id: str, request: Request):
    """Update editable fields on a draft cron profile."""
    try:
        body = await request.json()
        result = update_draft_cron_profile(
            profile_id,
            updates={
                "name": body.get("name"),
                "prompt_template": body.get("prompt_template"),
                "model": body.get("model"),
            },
        )
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": result.get(
                        "message", "Profile update failed"
                    )
                },
            )
        return result
    except Exception as exc:
        logger.error(
            "Failed to update cron profile %s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/cron-profiles/{profile_id}/archive")
async def api_archive_cron_profile(profile_id: str):
    """Archive a cron profile."""
    try:
        result = archive_cron_profile(profile_id)
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": result.get("message", "Archive failed")
                },
            )
        return result
    except Exception as exc:
        logger.error(
            "Failed to archive cron profile %s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.delete("/api/cron-profiles/{profile_id}")
async def api_delete_cron_profile(profile_id: str):
    """Delete a cron profile."""
    try:
        result = delete_cron_profile(profile_id)
        if not result.get("deleted"):
            return JSONResponse(
                status_code=404,
                content={
                    "error": result.get("message", "Delete failed")
                },
            )
        return result
    except Exception as exc:
        logger.error(
            "Failed to delete cron profile %s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/cron-profiles/{profile_id}/restore")
async def api_restore_cron_profile(profile_id: str):
    """Restore an archived cron profile to draft."""
    try:
        result = restore_cron_profile(profile_id)
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": result.get("message", "Restore failed")
                },
            )
        return result
    except Exception as exc:
        logger.error(
            "Failed to restore cron profile %s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post("/api/cron-profiles/{profile_id}/duplicate")
async def api_duplicate_cron_profile(profile_id: str):
    """Duplicate a cron profile into a new draft."""
    try:
        result = duplicate_cron_profile(profile_id)
        if not result.get("profile"):
            return JSONResponse(
                status_code=400,
                content={
                    "error": result.get("message", "Duplicate failed")
                },
            )
        return result
    except Exception as exc:
        logger.error(
            "Failed to duplicate cron profile %s: %s", profile_id, exc
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.get("/api/cron-profiles/{profile_id}/automation")
async def api_cron_profile_automation(profile_id: str):
    """Return a suggested Codex automation for an active cron profile."""
    try:
        result = load_cron_profile(profile_id)
        profile = result.get("profile")
        if not profile:
            return JSONResponse(
                status_code=404,
                content={
                    "error": result.get(
                        "message", "Cron profile not found"
                    )
                },
            )
        if profile.get("status") != "active":
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Only active cron profiles can generate automation suggestions."
                },
            )
        return build_automation_suggestion(profile, cwd=Path.cwd())
    except Exception as exc:
        logger.error(
            "Failed to build automation suggestion for cron profile %s: %s",
            profile_id,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )
