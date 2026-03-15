"""Recurring workflow and cron optimization analysis helpers.

Phase 1 is analysis-only. It detects recurring prompt hashes and classifies
them as likely static recurring prompts or dynamic recurring workflows.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruleshield.hermes_runner import run_compact_task
import re

RULESHIELD_DIR = Path.home() / ".ruleshield"
CRON_PROFILES_DIR = RULESHIELD_DIR / "cron_profiles"
CRON_PROFILE_DRAFTS_DIR = CRON_PROFILES_DIR / "drafts"
CRON_PROFILE_ACTIVE_DIR = CRON_PROFILES_DIR / "active"
CRON_PROFILE_ARCHIVE_DIR = CRON_PROFILES_DIR / "archived"
DEFAULT_ACTIVATION_MIN_RUNS = 2
DEFAULT_ACTIVATION_MIN_CONFIDENCE = 0.7

_SCHEDULE_HINTS = (
    "every day",
    "daily",
    "every morning",
    "every evening",
    "every week",
    "weekly",
    "every month",
    "monthly",
    "schedule",
    "at 8",
    "at 9",
    "at 10",
    "am",
    "pm",
)

_WORKFLOW_HINTS = (
    "check",
    "fetch",
    "sort",
    "categorize",
    "summarize",
    "return",
    "format",
    "send",
    "group",
    "digest",
    "report",
    "summarise",
)

_DYNAMIC_HINTS = (
    "mails",
    "emails",
    "inbox",
    "messages",
    "content",
    "news",
    "logs",
    "report",
    "server status",
    "updates",
)

_CONTROL_HINTS = (
    "every day",
    "daily",
    "every week",
    "weekly",
    "schedule",
    "at ",
)

_PREPROCESS_HINTS = (
    "sort",
    "categorize",
    "group",
    "filter",
    "classify",
    "organize",
)

_FETCH_HINTS = (
    "check",
    "fetch",
    "read",
    "pull",
    "get",
    "collect",
    "load",
    "scan",
)

_LLM_TASK_HINTS = (
    "summarize",
    "summarise",
    "explain",
    "analyze",
    "analyse",
    "rewrite",
)

_POSTPROCESS_HINTS = (
    "return",
    "format",
    "send",
    "output",
    "deliver",
    "post",
)

def _split_clauses(prompt_text: str) -> list[str]:
    """Split a workflow-like prompt into rough clauses."""
    text = " ".join(prompt_text.strip().split())
    if not text:
        return []

    normalized = (
        text.replace(" and then ", " | ")
        .replace(" then ", " | ")
        .replace(", then ", " | ")
        .replace(", and ", " | ")
        .replace(" and ", " | ")
    )
    return [clause.strip() for clause in normalized.split("|") if clause.strip()]


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(hint in lower for hint in hints)


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value[:48] or "cron_profile"


def _decompose_prompt(prompt_text: str) -> dict[str, list[str]]:
    """Classify clauses into rough workflow stages."""
    stages = {
        "control_steps": [],
        "fetch_steps": [],
        "preprocess_steps": [],
        "llm_task_steps": [],
        "postprocess_steps": [],
        "unclassified_steps": [],
    }

    for clause in _split_clauses(prompt_text):
        lower = clause.lower()
        matched = False
        if _contains_any(lower, _CONTROL_HINTS):
            stages["control_steps"].append(clause)
            matched = True
        if _contains_any(lower, _FETCH_HINTS):
            stages["fetch_steps"].append(clause)
            matched = True
        if _contains_any(lower, _PREPROCESS_HINTS):
            stages["preprocess_steps"].append(clause)
            matched = True
        if _contains_any(lower, _LLM_TASK_HINTS):
            stages["llm_task_steps"].append(clause)
            matched = True
        if _contains_any(lower, _POSTPROCESS_HINTS):
            stages["postprocess_steps"].append(clause)
            matched = True
        if not matched:
            stages["unclassified_steps"].append(clause)

    return stages


def _recommend_basic(cache_rate_pct: float) -> tuple[str, str]:
    """Return the legacy recurring-prompt recommendation."""
    if cache_rate_pct > 80:
        return "REPLACE", "already optimized -- direct rule/API candidate"
    if cache_rate_pct > 50:
        return "OPTIMIZE", "partially optimized -- compact prompt or add rule"
    return "MONITOR", "monitor -- not enough cache/rule reuse yet"


def ensure_cron_profile_dirs(base_dir: str | Path | None = None) -> dict[str, Path]:
    """Ensure the cron profile directory structure exists."""
    root = Path(base_dir).expanduser() if base_dir is not None else CRON_PROFILES_DIR
    drafts = root / "drafts"
    active = root / "active"
    archived = root / "archived"
    drafts.mkdir(parents=True, exist_ok=True)
    active.mkdir(parents=True, exist_ok=True)
    archived.mkdir(parents=True, exist_ok=True)
    return {"root": root, "drafts": drafts, "active": active, "archived": archived}


def _estimate_profile_savings(prompt_text: str, decomposition: dict[str, list[str]]) -> dict[str, float]:
    """Estimate compact prompt savings with simple heuristics."""
    original_tokens = max(1, len(prompt_text.split()))
    llm_text = " ".join(
        decomposition["llm_task_steps"] + decomposition["postprocess_steps"]
    ).strip()
    if not llm_text:
        llm_text = "Summarize this content."
    compact_tokens = max(1, len(llm_text.split()))
    token_reduction_pct = max(0.0, min(95.0, (1 - compact_tokens / original_tokens) * 100.0))

    deterministic_steps = (
        len(decomposition["control_steps"])
        + len(decomposition["fetch_steps"])
        + len(decomposition["preprocess_steps"])
        + len(decomposition["postprocess_steps"])
    )
    total_steps = max(1, deterministic_steps + len(decomposition["llm_task_steps"]))
    tool_reduction_pct = round((deterministic_steps / total_steps) * 100.0, 1)
    cost_reduction_pct = round(token_reduction_pct * 0.92, 1)

    return {
        "original_prompt_tokens_est": float(original_tokens),
        "compact_prompt_tokens_est": float(compact_tokens),
        "token_reduction_pct": round(token_reduction_pct, 1),
        "cost_reduction_pct": cost_reduction_pct,
        "tool_reduction_pct": tool_reduction_pct,
    }


def _build_compact_prompt(decomposition: dict[str, list[str]]) -> str:
    """Build the first compact prompt template for a draft profile."""
    llm_steps = decomposition["llm_task_steps"] or ["Summarize this content."]
    post_steps = decomposition["postprocess_steps"]

    prompt = " ".join(llm_steps).strip()
    if post_steps:
        prompt = f"{prompt} Output requirements: {'; '.join(post_steps)}."

    return prompt


def _infer_expected_output_format(postprocess_steps: list[str]) -> str:
    lower = " ".join(postprocess_steps).lower()
    if "markdown" in lower:
        return "markdown"
    if "json" in lower:
        return "json"
    if "email" in lower or "digest" in lower:
        return "digest"
    return "text"


def _build_profile_name(prompt_text: str) -> str:
    words = prompt_text.strip().split()
    preview = " ".join(words[:6]).strip()
    return preview.title() or "Cron Optimization Profile"


def _profile_id(prompt_hash: str, prompt_text: str) -> str:
    return f"{_slugify(prompt_text)[:32]}_{(prompt_hash or 'profile')[:8]}"


def _find_recurring_prompt(
    db_path: str | Path,
    prompt_hash_or_text: str,
    min_occurrences: int = 3,
    limit: int = 10,
) -> dict[str, Any]:
    """Find recurring prompt groups by hash prefix or prompt substring."""
    db_path = Path(db_path).expanduser()
    if not db_path.exists():
        return {"matches": [], "count": 0, "message": "No database found."}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        term = prompt_hash_or_text.strip()
        cur.execute(
            """
            SELECT prompt_hash,
                   MIN(prompt_text) as prompt_text,
                   MIN(model) as sample_model,
                   COUNT(*) as occurrences,
                   SUM(CASE WHEN resolution_type IN ('cache', 'rule') THEN 1 ELSE 0 END) as cached,
                   SUM(CASE WHEN resolution_type = 'llm' THEN 1 ELSE 0 END) as llm_hits,
                   COALESCE(SUM(cost_usd), 0) as total_cost,
                   COALESCE(AVG(latency_ms), 0) as avg_latency
            FROM request_log
            WHERE prompt_text IS NOT NULL AND prompt_text != ''
              AND (prompt_hash LIKE ? OR prompt_text LIKE ?)
            GROUP BY prompt_hash
            HAVING COUNT(*) >= ?
            ORDER BY occurrences DESC
            LIMIT ?
            """,
            (f"{term}%", f"%{term}%", min_occurrences, limit),
        )
        rows = cur.fetchall()
    except sqlite3.OperationalError as exc:
        return {"matches": [], "count": 0, "error": str(exc)}
    finally:
        conn.close()

    matches: list[dict[str, Any]] = []
    for row in rows:
        total = row["occurrences"] or 0
        cached = row["cached"] or 0
        cache_rate = (cached / total * 100.0) if total else 0.0
        prompt_text = row["prompt_text"] or ""
        match = {
            "prompt_hash": row["prompt_hash"],
            "prompt_text": prompt_text,
            "source_model": row["sample_model"] or "",
            "prompt_preview": prompt_text[:100] + ("..." if len(prompt_text) > 100 else ""),
            "occurrences": total,
            "cache_hits": cached,
            "llm_hits": row["llm_hits"] or 0,
            "cache_rate_pct": round(cache_rate, 1),
            "total_cost_usd": round(float(row["total_cost"] or 0.0), 6),
            "avg_latency_ms": round(float(row["avg_latency"] or 0.0), 1),
        }
        match.update(_classify_prompt(prompt_text, cache_rate))
        matches.append(match)

    return {
        "matches": matches,
        "count": len(matches),
        "message": f"Found {len(matches)} recurring prompt match(es)" if matches else "No matching recurring prompts found.",
    }


def suggest_cron_profile(
    db_path: str | Path,
    prompt_hash_or_text: str,
    *,
    min_occurrences: int = 3,
    profiles_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Create and persist a draft cron optimization profile from a recurring prompt."""
    search = _find_recurring_prompt(
        db_path,
        prompt_hash_or_text,
        min_occurrences=min_occurrences,
    )
    if search.get("error"):
        return search
    matches = search.get("matches", [])
    if not matches:
        return {"profile": None, "count": 0, "message": search.get("message", "No matching recurring prompts found.")}
    if len(matches) > 1:
        return {
            "profile": None,
            "count": 0,
            "message": "Multiple recurring prompt matches found. Narrow your search.",
            "matches": matches,
        }

    match = matches[0]
    decomposition = match["decomposition"]
    compact_prompt = _build_compact_prompt(decomposition)
    estimates = _estimate_profile_savings(match["prompt_text"], decomposition)
    directories = ensure_cron_profile_dirs(profiles_dir)
    profile_id = _profile_id(match["prompt_hash"], match["prompt_text"])

    profile = {
        "id": profile_id,
        "name": _build_profile_name(match["prompt_text"]),
        "status": "draft",
        "source": {
            "prompt_hash": match["prompt_hash"],
            "prompt_text": match["prompt_text"],
            "model": match.get("source_model", "") or "gpt-5.1-codex-mini",
        },
        "detection": {
            "occurrences": match["occurrences"],
            "cache_rate_pct": match["cache_rate_pct"],
            "schedule_like": match["schedule_like"],
            "workflow_like": match["workflow_like"],
            "dynamic_payload": match["dynamic_payload"],
            "classification": match["classification"],
        },
        "decomposition": decomposition,
        "optimized_execution": {
            "input_binding": "workflow_payload",
            "prompt_template": compact_prompt,
            "model": match.get("source_model", "") or "gpt-5.1-codex-mini",
            "expected_output_format": _infer_expected_output_format(decomposition["postprocess_steps"]),
        },
        "estimates": estimates,
        "validation": {
            "shadow_runs": 0,
            "avg_similarity": 0.0,
            "acceptance_rate": 0.0,
            "optimization_confidence": 0.0,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    profile_path = directories["drafts"] / f"{profile_id}.json"
    with open(profile_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)

    return {
        "profile": profile,
        "count": 1,
        "saved_path": str(profile_path),
        "message": "Draft cron optimization profile created.",
    }


def list_cron_profiles(profiles_dir: str | Path | None = None) -> dict[str, Any]:
    """List all stored draft and active cron profiles."""
    directories = ensure_cron_profile_dirs(profiles_dir)
    profiles: list[dict[str, Any]] = []

    for status, directory in (
        ("draft", directories["drafts"]),
        ("active", directories["active"]),
        ("archived", directories["archived"]),
    ):
        for path in sorted(directory.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as fh:
                    profile = json.load(fh)
            except Exception:
                continue
            profiles.append({
                "id": profile.get("id", path.stem),
                "name": profile.get("name", path.stem),
                "status": profile.get("status", status),
                "runtime_status": profile.get("runtime_status", "draft" if status == "draft" else status),
                "classification": profile.get("detection", {}).get("classification", "unknown"),
                "occurrences": profile.get("detection", {}).get("occurrences", 0),
                "token_reduction_pct": profile.get("estimates", {}).get("token_reduction_pct", 0.0),
                "optimization_confidence": profile.get("validation", {}).get("optimization_confidence", 0.0),
                "shadow_runs": profile.get("validation", {}).get("shadow_runs", 0),
                "last_validated_at": profile.get("validation", {}).get("last_validated_at", ""),
                "last_run_at": profile.get("last_run_at", ""),
                "path": str(path),
            })

    return {
        "profiles": profiles,
        "count": len(profiles),
        "message": f"Found {len(profiles)} cron profile(s).",
    }


def load_cron_profile(profile_id: str, profiles_dir: str | Path | None = None) -> dict[str, Any]:
    """Load a cron profile by id from draft or active storage."""
    directories = ensure_cron_profile_dirs(profiles_dir)
    for directory in (directories["drafts"], directories["active"], directories["archived"]):
        path = directory / f"{profile_id}.json"
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as fh:
            profile = json.load(fh)
        return {"profile": profile, "path": str(path)}

    return {"profile": None, "message": f"Cron profile not found: {profile_id}"}


def archive_cron_profile(
    profile_id: str,
    *,
    profiles_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Move a cron profile into archived storage."""
    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"profile": None, "message": f"Cron profile not found: {profile_id}"}

    current_path = Path(profile_result["path"])
    directories = ensure_cron_profile_dirs(profiles_dir)
    target_path = directories["archived"] / f"{profile_id}.json"

    profile["status"] = "archived"
    profile["runtime_status"] = "archived"
    profile["archived_at"] = datetime.now(timezone.utc).isoformat()

    with open(target_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)

    if current_path != target_path and current_path.exists():
        current_path.unlink()

    return {"profile": profile, "path": str(target_path), "message": "Cron profile archived."}


def restore_cron_profile(
    profile_id: str,
    *,
    profiles_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Restore an archived cron profile back to draft state."""
    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"profile": None, "message": f"Cron profile not found: {profile_id}"}
    if profile.get("status") != "archived":
        return {"profile": None, "message": f"Cron profile is not archived: {profile_id}"}

    current_path = Path(profile_result["path"])
    directories = ensure_cron_profile_dirs(profiles_dir)
    target_path = directories["drafts"] / f"{profile_id}.json"

    profile["status"] = "draft"
    profile["runtime_status"] = "draft"
    profile["restored_at"] = datetime.now(timezone.utc).isoformat()

    with open(target_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)

    if current_path != target_path and current_path.exists():
        current_path.unlink()

    return {"profile": profile, "path": str(target_path), "message": "Cron profile restored to draft."}


def duplicate_cron_profile(
    profile_id: str,
    *,
    profiles_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Create a draft copy of an existing cron profile."""
    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"profile": None, "message": f"Cron profile not found: {profile_id}"}

    directories = ensure_cron_profile_dirs(profiles_dir)
    duplicate_id = f"{profile_id}_copy"
    duplicate_path = directories["drafts"] / f"{duplicate_id}.json"
    suffix = 2
    while duplicate_path.exists():
        duplicate_id = f"{profile_id}_copy_{suffix}"
        duplicate_path = directories["drafts"] / f"{duplicate_id}.json"
        suffix += 1

    duplicate = json.loads(json.dumps(profile))
    duplicate["id"] = duplicate_id
    duplicate["name"] = f"{profile.get('name', profile_id)} Copy"
    duplicate["status"] = "draft"
    duplicate["runtime_status"] = "draft"
    duplicate["duplicated_from"] = profile_id
    duplicate["created_at"] = datetime.now(timezone.utc).isoformat()

    with open(duplicate_path, "w", encoding="utf-8") as fh:
        json.dump(duplicate, fh, indent=2, ensure_ascii=False)

    return {"profile": duplicate, "path": str(duplicate_path), "message": "Cron profile duplicated as draft."}


def delete_cron_profile(
    profile_id: str,
    *,
    profiles_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Delete a cron profile file permanently."""
    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"deleted": False, "message": f"Cron profile not found: {profile_id}"}

    current_path = Path(profile_result["path"])
    if current_path.exists():
        current_path.unlink()

    return {"deleted": True, "profile_id": profile_id, "message": "Cron profile deleted."}


def update_draft_cron_profile(
    profile_id: str,
    *,
    updates: dict[str, Any],
    profiles_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Update editable fields on a draft cron profile."""
    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"profile": None, "message": f"Cron profile not found: {profile_id}"}
    if profile.get("status") != "draft":
        return {"profile": None, "message": f"Only draft profiles can be edited: {profile_id}"}

    name = str(updates.get("name", profile.get("name", ""))).strip()
    prompt_template = str(
        updates.get(
            "prompt_template",
            profile.get("optimized_execution", {}).get("prompt_template", ""),
        )
    ).strip()
    model = str(
        updates.get(
            "model",
            profile.get("optimized_execution", {}).get("model", ""),
        )
    ).strip()

    if not name:
        return {"profile": None, "message": "Profile name cannot be empty."}
    if not prompt_template:
        return {"profile": None, "message": "Compact prompt cannot be empty."}
    if not model:
        return {"profile": None, "message": "Model cannot be empty."}

    profile["name"] = name
    profile.setdefault("optimized_execution", {})
    profile["optimized_execution"]["prompt_template"] = prompt_template
    profile["optimized_execution"]["model"] = model
    profile["updated_at"] = datetime.now(timezone.utc).isoformat()

    profile_path = Path(profile_result["path"])
    with open(profile_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)

    return {
        "profile": profile,
        "path": str(profile_path),
        "message": "Draft cron profile updated.",
    }


def activate_cron_profile(
    profile_id: str,
    *,
    db_path: str | Path,
    profiles_dir: str | Path | None = None,
    force: bool = False,
    min_runs: int = DEFAULT_ACTIVATION_MIN_RUNS,
    min_confidence: float = DEFAULT_ACTIVATION_MIN_CONFIDENCE,
) -> dict[str, Any]:
    """Promote a validated draft cron profile to active status."""
    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"profile": None, "message": f"Cron profile not found: {profile_id}"}

    current_path = Path(profile_result["path"])
    directories = ensure_cron_profile_dirs(profiles_dir)
    target_path = directories["active"] / f"{profile_id}.json"

    if profile.get("status") == "active" and target_path.exists():
        return {
            "profile": profile,
            "path": str(target_path),
            "message": f"Cron profile already active: {profile_id}",
        }

    from ruleshield.cron_validation import get_profile_validation_summary

    summary = get_profile_validation_summary(db_path, profile_id)
    total_runs = summary.get("total_runs", 0)
    confidence = summary.get("avg_optimization_confidence", 0.0)

    if not force:
        if total_runs < min_runs:
            return {
                "profile": None,
                "message": (
                    f"Activation blocked: profile has {total_runs} validation run(s); "
                    f"need at least {min_runs}."
                ),
                "summary": summary,
            }
        if confidence < min_confidence:
            return {
                "profile": None,
                "message": (
                    f"Activation blocked: optimization confidence {confidence:.2f} "
                    f"is below {min_confidence:.2f}."
                ),
                "summary": summary,
            }

    profile["status"] = "active"
    profile["runtime_status"] = "ready"
    profile["activated_at"] = datetime.now(timezone.utc).isoformat()
    profile["activation"] = {
        "forced": force,
        "min_runs_required": min_runs,
        "min_confidence_required": min_confidence,
        "summary_at_activation": summary,
    }

    with open(target_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)

    if current_path != target_path and current_path.exists():
        current_path.unlink()

    return {
        "profile": profile,
        "path": str(target_path),
        "summary": summary,
        "message": "Cron profile activated.",
    }


def execute_active_cron_profile(
    profile_id: str,
    payload_text: str,
    *,
    db_path: str | Path | None = None,
    profiles_dir: str | Path | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Execute an active cron profile with a supplied payload."""
    if not payload_text.strip():
        return {"execution": None, "message": "payload_text is required"}

    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"execution": None, "message": f"Cron profile not found: {profile_id}"}
    if profile.get("status") != "active":
        return {"execution": None, "message": f"Cron profile is not active: {profile_id}"}

    execution = run_compact_task(
        prompt_template=profile.get("optimized_execution", {}).get("prompt_template", ""),
        payload_text=payload_text,
        model=model or profile.get("optimized_execution", {}).get("model") or profile.get("source", {}).get("model") or "gpt-5.1-codex-mini",
    )

    profile["runtime_status"] = "ready"
    profile["last_run_at"] = datetime.now(timezone.utc).isoformat()
    profile["last_execution"] = {
        "model": execution.get("model", ""),
        "response_preview": (execution.get("response_text", "") or "")[:280],
    }

    if db_path is not None:
        from ruleshield.cron_execution import record_profile_execution

        record_profile_execution(
            db_path,
            profile_id,
            payload_text=payload_text,
            model=execution.get("model", ""),
            response_text=execution.get("response_text", "") or "",
        )

    profile_path = Path(profile_result["path"])
    with open(profile_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)

    return {
        "execution": execution,
        "profile": profile,
        "path": str(profile_path),
        "message": "Cron profile executed.",
    }


def _classify_prompt(prompt_text: str, cache_rate_pct: float) -> dict[str, Any]:
    """Classify a prompt as a static recurring prompt or dynamic workflow."""
    lower = prompt_text.lower()
    schedule_like = _contains_any(lower, _SCHEDULE_HINTS)
    workflow_actions = sum(1 for hint in _WORKFLOW_HINTS if hint in lower)
    dynamic_signals = sum(1 for hint in _DYNAMIC_HINTS if hint in lower)
    workflow_like = workflow_actions >= 2 or schedule_like
    dynamic_payload = dynamic_signals >= 1

    decomposition = _decompose_prompt(prompt_text)
    stage_count = sum(len(v) for v in decomposition.values() if v)

    if cache_rate_pct >= 80 or (workflow_like and not dynamic_payload):
        classification = "static_recurring"
    elif workflow_like and dynamic_payload:
        classification = "dynamic_workflow"
    else:
        classification = "monitor"

    if classification == "dynamic_workflow":
        recommendation = "profile candidate -- decompose and compact prompt"
    elif classification == "static_recurring":
        recommendation = "replace or promote -- direct rule/API candidate"
    else:
        recommendation = "monitor -- not enough workflow evidence yet"

    return {
        "schedule_like": schedule_like,
        "workflow_like": workflow_like,
        "dynamic_payload": dynamic_payload,
        "workflow_actions": workflow_actions,
        "stage_count": stage_count,
        "classification": classification,
        "recommendation": recommendation,
        "decomposition": decomposition,
    }


def _query_recurring_prompts(
    db_path: Path,
    min_occurrences: int,
    limit: int,
) -> tuple[list[sqlite3.Row], str | None]:
    """Fetch recurring prompt groups from request_log."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT prompt_hash,
                   MIN(prompt_text) as sample_prompt,
                   MIN(model) as sample_model,
                   COUNT(*) as occurrences,
                   SUM(CASE WHEN resolution_type IN ('cache', 'rule') THEN 1 ELSE 0 END) as cached,
                   SUM(CASE WHEN resolution_type = 'llm' THEN 1 ELSE 0 END) as llm_hits,
                   COALESCE(SUM(cost_usd), 0) as total_cost,
                   COALESCE(AVG(latency_ms), 0) as avg_latency
            FROM request_log
            WHERE prompt_text IS NOT NULL AND prompt_text != ''
            GROUP BY prompt_hash
            HAVING COUNT(*) >= ?
            ORDER BY occurrences DESC
            LIMIT ?
            """,
            (min_occurrences, limit),
        )
        return cur.fetchall(), None
    except sqlite3.OperationalError as exc:
        return [], str(exc)
    finally:
        conn.close()


def analyze_recurring_workflows(
    db_path: str | Path,
    min_occurrences: int = 5,
    *,
    structured: bool = True,
    limit: int = 20,
) -> dict[str, Any]:
    """Analyze recurring prompts and classify cron/workflow optimization opportunities."""
    db_path = Path(db_path).expanduser()
    if not db_path.exists():
        return {"candidates": [], "count": 0, "message": "No database found."}

    rows, error = _query_recurring_prompts(
        db_path,
        min_occurrences=min_occurrences,
        limit=limit,
    )
    if error:
        return {"candidates": [], "count": 0, "error": error}

    if not rows:
        return {
            "candidates": [],
            "count": 0,
            "message": f"No prompts found with {min_occurrences}+ occurrences.",
        }

    candidates: list[dict[str, Any]] = []
    for row in rows:
        total = row["occurrences"] or 0
        cached = row["cached"] or 0
        llm_hits = row["llm_hits"] or 0
        cache_rate = (cached / total * 100.0) if total > 0 else 0.0
        prompt_text = row["sample_prompt"] or ""
        prompt_preview = prompt_text[:100] + ("..." if len(prompt_text) > 100 else "")
        candidate = {
            "prompt_hash": row["prompt_hash"],
            "prompt_hash_short": (row["prompt_hash"] or "")[:16] + "...",
            "prompt_text": prompt_text,
            "source_model": row["sample_model"] or "",
            "prompt_preview": prompt_preview,
            "occurrences": total,
            "cache_hits": cached,
            "llm_hits": llm_hits,
            "cache_rate_pct": round(cache_rate, 1),
            "total_cost_usd": round(float(row["total_cost"] or 0.0), 6),
            "avg_latency_ms": round(float(row["avg_latency"] or 0.0), 1),
        }

        if structured:
            candidate.update(_classify_prompt(prompt_text, cache_rate))
        else:
            recommendation_label, recommendation = _recommend_basic(cache_rate)
            candidate.update({
                "recommendation_label": recommendation_label,
                "recommendation": recommendation,
            })

        candidates.append(candidate)

    by_classification: dict[str, int] = {}
    if structured:
        for candidate in candidates:
            key = candidate["classification"]
            by_classification[key] = by_classification.get(key, 0) + 1

    result = {
        "candidates": candidates,
        "count": len(candidates),
        "message": f"Found {len(candidates)} recurring prompt(s) with {min_occurrences}+ occurrences",
    }
    if structured:
        result["summary"] = by_classification
    return result
