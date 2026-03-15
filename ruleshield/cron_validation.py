"""Cron profile shadow validation helpers.

Phase 3 keeps validation simple and explicit:
- load a draft profile
- compare one optimized output against recent original outputs
- persist validation evidence in SQLite
- update the profile-level validation summary
"""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from ruleshield.hermes_runner import run_compact_task
from ruleshield.cron_optimizer import CRON_PROFILES_DIR, load_cron_profile


def _tokenize(text: str) -> set[str]:
    return {word for word in text.lower().split() if word}


def _normalize_text(text: str) -> str:
    """Normalize text for lightweight semantic comparison."""
    normalized = text.lower()
    normalized = re.sub(r"[^\w\s#*\-:]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _extract_response_text(raw_response: str) -> str:
    """Extract assistant text from a stored request_log response payload."""
    if not raw_response:
        return ""
    try:
        payload = json.loads(raw_response)
    except Exception:
        return raw_response

    if isinstance(payload, dict):
        for choice in payload.get("choices", []):
            message = choice.get("message", {})
            content = message.get("content", "")
            if content:
                return str(content)
        content = payload.get("content", "")
        if isinstance(content, str) and content:
            return content

    return raw_response


def compare_outputs(
    original_response: str,
    optimized_response: str,
    expected_output_format: str = "text",
) -> dict[str, Any]:
    """Compare original and optimized outputs using simple validation primitives."""
    original_text = original_response.strip()
    optimized_text = optimized_response.strip()
    normalized_original = _normalize_text(original_text)
    normalized_optimized = _normalize_text(optimized_text)
    original_words = _tokenize(normalized_original)
    optimized_words = _tokenize(normalized_optimized)

    if original_words or optimized_words:
        union = original_words | optimized_words
        token_similarity = len(original_words & optimized_words) / len(union) if union else 0.0
    else:
        token_similarity = 1.0

    sequence_similarity = difflib.SequenceMatcher(
        None,
        normalized_original,
        normalized_optimized,
    ).ratio()

    original_len = len(original_text)
    optimized_len = len(optimized_text)
    if max(original_len, optimized_len) > 0:
        length_ratio = min(original_len, optimized_len) / max(original_len, optimized_len)
    else:
        length_ratio = 1.0

    if expected_output_format == "markdown":
        structure_score = 1.0 if ("#" in optimized_text or "-" in optimized_text or "*" in optimized_text) else 0.4
    elif expected_output_format == "json":
        try:
            json.loads(optimized_text)
            structure_score = 1.0
        except Exception:
            structure_score = 0.0
    elif expected_output_format == "digest":
        structure_score = 1.0 if ":" in optimized_text or "\n" in optimized_text else 0.5
    else:
        structure_score = 1.0 if optimized_text else 0.0

    line_count_original = max(1, len([line for line in original_text.splitlines() if line.strip()]))
    line_count_optimized = max(1, len([line for line in optimized_text.splitlines() if line.strip()]))
    line_ratio = min(line_count_original, line_count_optimized) / max(line_count_original, line_count_optimized)
    similarity = (0.55 * token_similarity) + (0.3 * sequence_similarity) + (0.15 * line_ratio)

    if similarity >= 0.8:
        match_quality = "good"
    elif similarity >= 0.4:
        match_quality = "partial"
    else:
        match_quality = "poor"

    return {
        "similarity": round(similarity, 4),
        "length_ratio": round(length_ratio, 4),
        "structure_score": round(structure_score, 4),
        "match_quality": match_quality,
    }


def compute_optimization_confidence(
    similarity: float,
    structure_score: float,
    acceptance_rate: float = 0.0,
) -> float:
    """Compute a profile-level optimization confidence score."""
    return round(
        max(0.0, min(1.0, (0.6 * similarity) + (0.2 * structure_score) + (0.2 * acceptance_rate))),
        4,
    )


def init_validation_db(db_path: str | Path) -> None:
    """Ensure the cron validation table exists."""
    db_path = Path(db_path).expanduser()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cron_profile_validation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                prompt_text TEXT,
                original_response TEXT,
                optimized_response TEXT,
                similarity REAL,
                length_ratio REAL,
                structure_score REAL,
                optimization_confidence REAL,
                match_quality TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _update_profile_validation_summary(
    profile_id: str,
    db_path: str | Path,
    profiles_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Refresh the stored validation summary inside the profile artifact."""
    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"profile": None, "message": f"Cron profile not found: {profile_id}"}

    summary = get_profile_validation_summary(db_path, profile_id)
    profile["validation"] = {
        "shadow_runs": summary["total_runs"],
        "avg_similarity": summary["avg_similarity"],
        "acceptance_rate": summary["acceptance_rate"],
        "optimization_confidence": summary["avg_optimization_confidence"],
        "avg_structure_score": summary["avg_structure_score"],
        "last_validated_at": summary["last_validated_at"],
    }

    profile_path = Path(profile_result["path"])
    with open(profile_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)

    return {"profile": profile, "path": str(profile_path)}


def run_cron_shadow(
    db_path: str | Path,
    profile_id: str,
    optimized_response: str = "",
    *,
    sample_limit: int = 3,
    payload_text: str = "",
    model: str | None = None,
    profiles_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Compare an optimized output against recent original outputs for a profile."""
    db_path = Path(db_path).expanduser()
    profile_result = load_cron_profile(profile_id, profiles_dir=profiles_dir)
    profile = profile_result.get("profile")
    if not profile:
        return {"runs": [], "count": 0, "message": f"Cron profile not found: {profile_id}"}

    if not optimized_response.strip():
        if not payload_text.strip():
            return {"runs": [], "count": 0, "message": "optimized_response or payload_text is required"}
        execution = run_compact_task(
            prompt_template=profile["optimized_execution"].get("prompt_template", ""),
            payload_text=payload_text,
            model=model or profile["optimized_execution"].get("model") or profile["source"].get("model") or "gpt-5.1-codex-mini",
        )
        optimized_response = execution.get("response_text", "")
    else:
        execution = None

    init_validation_db(db_path)

    source = profile["source"]
    expected_output_format = profile["optimized_execution"].get("expected_output_format", "text")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT prompt_text, response
            FROM request_log
            WHERE prompt_hash = ?
              AND response IS NOT NULL
              AND response != ''
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (source["prompt_hash"], sample_limit),
        )
        samples = cur.fetchall()

        runs: list[dict[str, Any]] = []
        for sample in samples:
            original_text = _extract_response_text(sample["response"] or "")
            comparison = compare_outputs(
                original_text,
                optimized_response,
                expected_output_format=expected_output_format,
            )
            optimization_confidence = compute_optimization_confidence(
                comparison["similarity"],
                comparison["structure_score"],
                1.0 if comparison["match_quality"] == "good" else 0.0,
            )

            conn.execute(
                """
                INSERT INTO cron_profile_validation
                    (profile_id, prompt_hash, prompt_text, original_response, optimized_response,
                     similarity, length_ratio, structure_score, optimization_confidence, match_quality)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    source["prompt_hash"],
                    sample["prompt_text"] or source["prompt_text"],
                    original_text,
                    optimized_response,
                    comparison["similarity"],
                    comparison["length_ratio"],
                    comparison["structure_score"],
                    optimization_confidence,
                    comparison["match_quality"],
                ),
            )

            runs.append({
                "prompt_text": sample["prompt_text"] or source["prompt_text"],
                "original_response": original_text,
                "optimized_response": optimized_response,
                **comparison,
                "optimization_confidence": optimization_confidence,
            })

        conn.commit()
    finally:
        conn.close()

    summary = get_profile_validation_summary(db_path, profile_id)
    _update_profile_validation_summary(profile_id, db_path, profiles_dir=profiles_dir)

    return {
        "runs": runs,
        "count": len(runs),
        "summary": summary,
        "optimized_response": optimized_response,
        "execution": execution,
        "message": f"Stored {len(runs)} cron shadow validation run(s).",
    }


def get_profile_validation_summary(
    db_path: str | Path,
    profile_id: str,
) -> dict[str, Any]:
    """Return validation summary stats for one profile."""
    db_path = Path(db_path).expanduser()
    init_validation_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COUNT(*) as total_runs,
                AVG(similarity) as avg_similarity,
                AVG(structure_score) as avg_structure_score,
                AVG(optimization_confidence) as avg_optimization_confidence,
                SUM(CASE WHEN match_quality = 'good' THEN 1 ELSE 0 END) as good_runs,
                MAX(created_at) as last_validated_at
            FROM cron_profile_validation
            WHERE profile_id = ?
            """,
            (profile_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    total_runs = int(row[0] or 0) if row else 0
    good_runs = int(row[4] or 0) if row else 0
    acceptance_rate = round((good_runs / total_runs) if total_runs else 0.0, 4)

    return {
        "profile_id": profile_id,
        "total_runs": total_runs,
        "avg_similarity": round(float(row[1] or 0.0), 4) if row else 0.0,
        "avg_structure_score": round(float(row[2] or 0.0), 4) if row else 0.0,
        "avg_optimization_confidence": round(float(row[3] or 0.0), 4) if row else 0.0,
        "acceptance_rate": acceptance_rate,
        "last_validated_at": row[5] if row and row[5] else "",
    }


def get_profile_validation_history(
    db_path: str | Path,
    profile_id: str,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Return recent validation runs for one profile."""
    db_path = Path(db_path).expanduser()
    init_validation_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                id,
                prompt_text,
                original_response,
                optimized_response,
                similarity,
                length_ratio,
                structure_score,
                optimization_confidence,
                match_quality,
                created_at
            FROM cron_profile_validation
            WHERE profile_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (profile_id, limit),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    runs = []
    for row in rows:
        runs.append({
            "id": int(row["id"] or 0),
            "prompt_text": row["prompt_text"] or "",
            "original_response": row["original_response"] or "",
            "optimized_response": row["optimized_response"] or "",
            "similarity": round(float(row["similarity"] or 0.0), 4),
            "similarity_pct": round(float(row["similarity"] or 0.0) * 100, 1),
            "length_ratio": round(float(row["length_ratio"] or 0.0), 4),
            "structure_score": round(float(row["structure_score"] or 0.0), 4),
            "structure_score_pct": round(float(row["structure_score"] or 0.0) * 100, 1),
            "optimization_confidence": round(float(row["optimization_confidence"] or 0.0), 4),
            "optimization_confidence_pct": round(float(row["optimization_confidence"] or 0.0) * 100, 1),
            "match_quality": row["match_quality"] or "unknown",
            "created_at": row["created_at"] or "",
        })

    return {"profile_id": profile_id, "runs": runs, "count": len(runs)}
