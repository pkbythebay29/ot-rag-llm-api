from __future__ import annotations

from typing import Any

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.db import regulation_pool_store


def _normalize_asset(item: dict[str, Any]) -> dict[str, Any]:
    payload = dict(item)
    payload.setdefault("docs", [])
    return payload


def _pool_to_asset(pool: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": pool["name"],
        "docs_dir": pool.get("docs_dir"),
        "docs": list(pool.get("docs") or []),
        "description": pool.get("description"),
        "framework": pool.get("framework"),
        "focus": pool.get("focus"),
        "pool_type": "regulatory",
        "is_regulation_pool": True,
        "created_via": "api",
    }


def _static_pool_to_asset(pool: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": pool["name"],
        "docs_dir": pool.get("docs_dir"),
        "docs": list(pool.get("docs") or []),
        "description": pool.get("description"),
        "framework": pool.get("framework"),
        "focus": pool.get("focus"),
        "pool_type": "regulatory",
        "is_regulation_pool": True,
        "created_via": "config",
    }


def get_assets(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config() or {}
    static_assets = [
        _normalize_asset(asset)
        for asset in cfg.get("assets", [])
        if isinstance(asset, dict) and asset.get("name")
    ]

    merged = {asset["name"]: asset for asset in static_assets}
    static_pools = cfg.get("compliance", {}).get("regulation_pools") or []
    for pool in static_pools:
        if isinstance(pool, dict) and pool.get("name"):
            merged[pool["name"]] = _static_pool_to_asset(pool)
    for pool in regulation_pool_store.list_pools():
        if pool.get("name"):
            merged[pool["name"]] = _pool_to_asset(pool)
    return list(merged.values())


def find_asset(
    system_name: str, config: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    for asset in get_assets(config):
        if asset.get("name") == system_name:
            return asset
    return None


def list_regulation_pools(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    pools = []
    for asset in get_assets(config):
        if asset.get("is_regulation_pool"):
            pools.append(asset)
    return pools
