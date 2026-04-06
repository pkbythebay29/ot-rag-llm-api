from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core.hitl import utc_now_iso

DEFAULT_REVIEW_DB_PATH = os.path.join("data", "reviews", "review_queue.sqlite3")


def get_db_path() -> str:
    config = load_config() or {}
    store_cfg = config.get("review_store", {})
    return os.getenv("KRIONIS_REVIEW_DB_PATH") or store_cfg.get(
        "sqlite_path", DEFAULT_REVIEW_DB_PATH
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
            CREATE TABLE IF NOT EXISTS review_items (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                item_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_review(item: dict[str, Any]) -> dict[str, Any]:
    init_db()
    created_at = item.get("timestamps", {}).get("created_at") or utc_now_iso()
    updated_at = item.get("timestamps", {}).get("updated_at") or created_at
    payload = json.dumps(item, ensure_ascii=True, sort_keys=True)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO review_items (id, status, created_at, updated_at, item_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (item["id"], item["status"], created_at, updated_at, payload),
        )
        conn.commit()
    return item


def get_review(review_id: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT item_json FROM review_items WHERE id = ?", (review_id,)
        ).fetchone()
    if not row:
        return None
    return json.loads(row["item_json"])


def get_pending_reviews() -> list[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT item_json
            FROM review_items
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        ).fetchall()
    return [json.loads(row["item_json"]) for row in rows]


def update_review(review_id: str, item: dict[str, Any]) -> dict[str, Any]:
    init_db()
    item.setdefault("timestamps", {})
    item["timestamps"]["updated_at"] = utc_now_iso()
    payload = json.dumps(item, ensure_ascii=True, sort_keys=True)
    created_at = item["timestamps"].get("created_at") or item["timestamps"]["updated_at"]
    updated_at = item["timestamps"]["updated_at"]
    with _connect() as conn:
        conn.execute(
            """
            UPDATE review_items
            SET status = ?, created_at = ?, updated_at = ?, item_json = ?
            WHERE id = ?
            """,
            (item["status"], created_at, updated_at, payload, review_id),
        )
        conn.commit()
    return item
