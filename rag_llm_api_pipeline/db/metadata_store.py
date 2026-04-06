from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config

DEFAULT_METADATA_DB_PATH = os.path.join("data", "feedback", "result_metadata.sqlite3")


def get_db_path() -> str:
    config = load_config() or {}
    feedback_cfg = config.get("feedback", {})
    return os.getenv("KRIONIS_RESULTS_DB_PATH") or feedback_cfg.get(
        "metadata_sqlite_path", DEFAULT_METADATA_DB_PATH
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
            CREATE TABLE IF NOT EXISTS result_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                trace_id TEXT,
                review_id TEXT,
                status TEXT,
                rating TEXT,
                system_id TEXT,
                user_id TEXT,
                reviewer_id TEXT,
                created_at TEXT NOT NULL,
                record_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_record(
    *,
    event_type: str,
    created_at: str,
    payload: dict[str, Any],
    trace_id: str | None = None,
    review_id: str | None = None,
    status: str | None = None,
    rating: str | None = None,
    system_id: str | None = None,
    user_id: str | None = None,
    reviewer_id: str | None = None,
) -> dict[str, Any]:
    init_db()
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO result_records (
                event_type,
                trace_id,
                review_id,
                status,
                rating,
                system_id,
                user_id,
                reviewer_id,
                created_at,
                record_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                trace_id,
                review_id,
                status,
                rating,
                system_id,
                user_id,
                reviewer_id,
                created_at,
                encoded,
            ),
        )
        conn.commit()
    return payload


def list_records(limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    safe_limit = max(1, min(limit, 250))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                event_type,
                trace_id,
                review_id,
                status,
                rating,
                system_id,
                user_id,
                reviewer_id,
                created_at,
                record_json
            FROM result_records
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    records: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["record_json"])
        payload["_meta"] = {
            "id": row["id"],
            "event_type": row["event_type"],
            "trace_id": row["trace_id"],
            "review_id": row["review_id"],
            "status": row["status"],
            "rating": row["rating"],
            "system_id": row["system_id"],
            "user_id": row["user_id"],
            "reviewer_id": row["reviewer_id"],
            "created_at": row["created_at"],
        }
        records.append(payload)
    return records


def get_summary() -> dict[str, int]:
    init_db()
    summary = {
        "quality_good": 0,
        "quality_bad": 0,
        "reviews_approved": 0,
        "reviews_rejected": 0,
    }
    with _connect() as conn:
        for rating in ("good", "bad"):
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM result_records
                WHERE event_type = 'quality_feedback' AND rating = ?
                """,
                (rating,),
            ).fetchone()
            summary[f"quality_{rating}"] = int(row["count"] if row else 0)

        for status_name in ("approved", "rejected"):
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM result_records
                WHERE event_type = 'review_feedback' AND status = ?
                """,
                (status_name,),
            ).fetchone()
            summary[f"reviews_{status_name}"] = int(row["count"] if row else 0)

    return summary
