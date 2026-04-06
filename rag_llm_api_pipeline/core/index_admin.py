from __future__ import annotations

import os
import pickle
from datetime import datetime, timezone
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config


def _utc_iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def get_index_dir(config: dict[str, Any] | None = None) -> str:
    cfg = config or load_config() or {}
    return cfg.get("retriever", {}).get("index_dir", "indices")


def get_system_data_dir(system_name: str, config: dict[str, Any] | None = None) -> str:
    cfg = config or load_config() or {}
    system = next((a for a in cfg.get("assets", []) if a.get("name") == system_name), None)
    if not system:
        raise ValueError(f"System '{system_name}' not found in assets list.")
    return system.get("docs_dir") or cfg.get("settings", {}).get("data_dir", "data/manuals")


def _list_source_files(system_name: str, config: dict[str, Any]) -> list[str]:
    system = next((a for a in config.get("assets", []) if a.get("name") == system_name), None)
    if not system:
        raise ValueError(f"System '{system_name}' not found in assets list.")

    data_dir = get_system_data_dir(system_name, config)
    docs = list(system.get("docs") or [])
    if docs:
        return docs
    if not os.path.isdir(data_dir):
        return []
    return sorted(
        name for name in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, name))
    )


def _chunk_count(texts_path: str) -> int | None:
    if not os.path.exists(texts_path):
        return None
    try:
        with open(texts_path, "rb") as handle:
            texts = pickle.load(handle)
        return len(texts) if isinstance(texts, list) else None
    except Exception:
        return None


def get_index_status(system_name: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or load_config() or {}
    index_dir = get_index_dir(cfg)
    data_dir = get_system_data_dir(system_name, cfg)
    source_files = _list_source_files(system_name, cfg)

    faiss_path = os.path.join(index_dir, f"{system_name}.faiss")
    texts_path = os.path.join(index_dir, f"{system_name}_texts.pkl")
    meta_path = os.path.join(index_dir, f"{system_name}_meta.pkl")
    normflag_path = os.path.join(index_dir, f"{system_name}.normflag")
    index_exists = all(
        os.path.exists(path) for path in (faiss_path, texts_path, meta_path, normflag_path)
    )
    last_built_ts = os.path.getmtime(faiss_path) if os.path.exists(faiss_path) else None

    return {
        "system_name": system_name,
        "source_directory": os.path.abspath(data_dir),
        "index_directory": os.path.abspath(index_dir),
        "source_files": source_files,
        "source_file_count": len(source_files),
        "index_exists": index_exists,
        "index_files": {
            "faiss": os.path.abspath(faiss_path),
            "texts": os.path.abspath(texts_path),
            "meta": os.path.abspath(meta_path),
            "normflag": os.path.abspath(normflag_path),
        },
        "indexed_chunk_count": _chunk_count(texts_path),
        "last_built_at": _utc_iso(last_built_ts),
    }


def list_index_statuses(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config() or {}
    statuses = []
    for asset in cfg.get("assets", []):
        name = asset.get("name")
        if name:
            statuses.append(get_index_status(name, cfg))
    return statuses
