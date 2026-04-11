from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config

DEFAULT_REGULATION_POOL_DB_PATH = os.path.join(
    "data", "compliance", "regulation_pools.sqlite3"
)


def get_db_path() -> str:
    config = load_config() or {}
    compliance_cfg = config.get("compliance", {})
    return os.getenv("KRIONIS_REGULATION_POOL_DB_PATH") or compliance_cfg.get(
        "pool_sqlite_path", DEFAULT_REGULATION_POOL_DB_PATH
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
            CREATE TABLE IF NOT EXISTS regulation_pools (
                name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                pool_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_pool(item: dict[str, Any]) -> dict[str, Any]:
    init_db()
    timestamps = item.get("timestamps", {})
    created_at = str(timestamps.get("created_at") or "")
    updated_at = str(timestamps.get("updated_at") or created_at)
    encoded = json.dumps(item, ensure_ascii=True, sort_keys=True)
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO regulation_pools (
                name,
                created_at,
                updated_at,
                pool_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (item["name"], created_at, updated_at, encoded),
        )
        conn.commit()
    return item


def get_pool(name: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT pool_json FROM regulation_pools WHERE name = ?", (name,)
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["pool_json"])


def list_pools() -> list[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT pool_json
            FROM regulation_pools
            ORDER BY updated_at DESC, created_at DESC
            """
        ).fetchall()
    return [json.loads(row["pool_json"]) for row in rows]
