"""Execution history for active cron optimization profiles."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def init_execution_db(db_path: str | Path) -> None:
    """Ensure the cron execution table exists."""
    db_path = Path(db_path).expanduser()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cron_profile_execution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT NOT NULL,
                payload_text TEXT,
                model TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def record_profile_execution(
    db_path: str | Path,
    profile_id: str,
    *,
    payload_text: str,
    model: str,
    response_text: str,
) -> dict[str, Any]:
    """Persist one active-profile execution."""
    db_path = Path(db_path).expanduser()
    init_execution_db(db_path)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO cron_profile_execution
                (profile_id, payload_text, model, response_text)
            VALUES (?, ?, ?, ?)
            """,
            (profile_id, payload_text, model, response_text),
        )
        conn.commit()
        execution_id = int(cur.lastrowid or 0)
    finally:
        conn.close()

    return {"id": execution_id, "profile_id": profile_id}


def get_profile_execution_history(
    db_path: str | Path,
    profile_id: str,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """Return recent active execution runs for one profile."""
    db_path = Path(db_path).expanduser()
    init_execution_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, payload_text, model, response_text, created_at
            FROM cron_profile_execution
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
        response_text = row["response_text"] or ""
        runs.append(
            {
                "id": int(row["id"] or 0),
                "payload_text": row["payload_text"] or "",
                "model": row["model"] or "",
                "response_text": response_text,
                "response_preview": response_text[:280],
                "created_at": row["created_at"] or "",
            }
        )

    return {"profile_id": profile_id, "runs": runs, "count": len(runs)}
