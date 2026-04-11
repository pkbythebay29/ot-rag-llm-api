from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config

DEFAULT_COMPLIANCE_DB_PATH = os.path.join("data", "compliance", "assessments.sqlite3")


def get_db_path() -> str:
    config = load_config() or {}
    compliance_cfg = config.get("compliance", {})
    return os.getenv("KRIONIS_COMPLIANCE_DB_PATH") or compliance_cfg.get(
        "sqlite_path", DEFAULT_COMPLIANCE_DB_PATH
    )


def _connect() -> sqlite3.Connection:
    path = get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS compliance_assessments (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                system_id TEXT,
                regulation_system TEXT,
                framework TEXT,
                focus TEXT,
                trace_id TEXT,
                review_id TEXT,
                user_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                assessment_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_assessment(item: dict[str, Any]) -> dict[str, Any]:
    init_db()
    payload = dict(item)
    timestamps = payload.get("timestamps", {})
    created_at = str(timestamps.get("created_at") or "")
    updated_at = str(timestamps.get("updated_at") or created_at)
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO compliance_assessments (
                id,
                status,
                system_id,
                regulation_system,
                framework,
                focus,
                trace_id,
                review_id,
                user_id,
                created_at,
                updated_at,
                assessment_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["id"],
                payload.get("status", "unknown"),
                payload.get("system_id"),
                payload.get("regulation_system"),
                payload.get("framework"),
                payload.get("focus"),
                payload.get("trace_id"),
                payload.get("review_id"),
                payload.get("user_id"),
                created_at,
                updated_at,
                encoded,
            ),
        )
        conn.commit()
    return payload


def update_assessment(assessment_id: str, item: dict[str, Any]) -> dict[str, Any]:
    payload = dict(item)
    payload["id"] = assessment_id
    return save_assessment(payload)


def get_assessment(assessment_id: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT assessment_json
            FROM compliance_assessments
            WHERE id = ?
            """,
            (assessment_id,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["assessment_json"])


def list_assessments(
    *, limit: int = 50, status: str | None = None
) -> list[dict[str, Any]]:
    init_db()
    safe_limit = max(1, min(limit, 250))
    query = """
        SELECT assessment_json
        FROM compliance_assessments
    """
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY updated_at DESC, created_at DESC LIMIT ?"
    params.append(safe_limit)

    with _connect() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [json.loads(row["assessment_json"]) for row in rows]


def get_summary() -> dict[str, int]:
    init_db()
    summary = {
        "total": 0,
        "pending_review": 0,
        "approved": 0,
        "rejected": 0,
    }
    with _connect() as conn:
        total_row = conn.execute(
            "SELECT COUNT(*) AS count FROM compliance_assessments"
        ).fetchone()
        summary["total"] = int(total_row["count"] if total_row else 0)
        for status_name in ("pending_review", "approved", "rejected"):
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM compliance_assessments
                WHERE status = ?
                """,
                (status_name,),
            ).fetchone()
            summary[status_name] = int(row["count"] if row else 0)
    return summary
