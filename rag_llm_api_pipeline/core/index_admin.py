from __future__ import annotations

import os
import pickle
from datetime import datetime, timezone
from typing import Any

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core.model_selection import (
    embedding_index_slug,
    resolve_runtime_selection,
)
from rag_llm_api_pipeline.core.system_assets import find_asset, get_assets


def _utc_iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def get_index_dir(config: dict[str, Any] | None = None) -> str:
    cfg = config or load_config() or {}
    return cfg.get("retriever", {}).get("index_dir", "indices")


def get_system_data_dir(system_name: str, config: dict[str, Any] | None = None) -> str:
    cfg = config or load_config() or {}
    system = find_asset(system_name, cfg)
    if not system:
        raise ValueError(f"System '{system_name}' not found in assets list.")
    return system.get("docs_dir") or cfg.get("settings", {}).get(
        "data_dir", "data/manuals"
    )


def _list_source_files(system_name: str, config: dict[str, Any]) -> list[str]:
    system = find_asset(system_name, config)
    if not system:
        raise ValueError(f"System '{system_name}' not found in assets list.")

    data_dir = get_system_data_dir(system_name, config)
    docs = list(system.get("docs") or [])
    if docs:
        return docs
    if not os.path.isdir(data_dir):
        return []
    return sorted(
        name
        for name in os.listdir(data_dir)
        if os.path.isfile(os.path.join(data_dir, name))
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


def _artifact_paths(
    index_dir: str, system_name: str, runtime: dict[str, Any]
) -> dict[str, str]:
    variant = embedding_index_slug(runtime)
    base = f"{system_name}--{variant}"
    return {
        "faiss": os.path.join(index_dir, f"{base}.faiss"),
        "texts": os.path.join(index_dir, f"{base}_texts.pkl"),
        "meta": os.path.join(index_dir, f"{base}_meta.pkl"),
        "normflag": os.path.join(index_dir, f"{base}.normflag"),
        "variant": variant,
    }


def _list_index_variants(index_dir: str, system_name: str) -> list[dict[str, Any]]:
    prefix = f"{system_name}--"
    variants: list[dict[str, Any]] = []
    if not os.path.isdir(index_dir):
        return variants

    for name in sorted(os.listdir(index_dir)):
        if not name.startswith(prefix) or not name.endswith(".faiss"):
            continue
        variant = name[len(prefix) : -len(".faiss")]
        faiss_path = os.path.join(index_dir, name)
        texts_path = os.path.join(index_dir, f"{system_name}--{variant}_texts.pkl")
        meta_path = os.path.join(index_dir, f"{system_name}--{variant}_meta.pkl")
        normflag_path = os.path.join(index_dir, f"{system_name}--{variant}.normflag")
        variants.append(
            {
                "variant": variant,
                "index_exists": all(
                    os.path.exists(path)
                    for path in (faiss_path, texts_path, meta_path, normflag_path)
                ),
                "indexed_chunk_count": _chunk_count(texts_path),
                "last_built_at": _utc_iso(os.path.getmtime(faiss_path)),
                "index_files": {
                    "faiss": os.path.abspath(faiss_path),
                    "texts": os.path.abspath(texts_path),
                    "meta": os.path.abspath(meta_path),
                    "normflag": os.path.abspath(normflag_path),
                },
            }
        )
    return variants


def get_index_status(
    system_name: str,
    config: dict[str, Any] | None = None,
    model_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_config() or {}
    index_dir = get_index_dir(cfg)
    data_dir = get_system_data_dir(system_name, cfg)
    source_files = _list_source_files(system_name, cfg)
    runtime = resolve_runtime_selection(
        cfg,
        system_name=system_name,
        overrides=model_selection,
    )
    artifacts = _artifact_paths(index_dir, system_name, runtime)

    index_exists = all(
        os.path.exists(path)
        for path in (
            artifacts["faiss"],
            artifacts["texts"],
            artifacts["meta"],
            artifacts["normflag"],
        )
    )
    last_built_ts = (
        os.path.getmtime(artifacts["faiss"])
        if os.path.exists(artifacts["faiss"])
        else None
    )

    return {
        "system_name": system_name,
        "source_directory": os.path.abspath(data_dir),
        "index_directory": os.path.abspath(index_dir),
        "source_files": source_files,
        "source_file_count": len(source_files),
        "index_exists": index_exists,
        "embedding_model": runtime["embedding_model"],
        "embedding_variant": artifacts["variant"],
        "index_files": {
            "faiss": os.path.abspath(artifacts["faiss"]),
            "texts": os.path.abspath(artifacts["texts"]),
            "meta": os.path.abspath(artifacts["meta"]),
            "normflag": os.path.abspath(artifacts["normflag"]),
        },
        "indexed_chunk_count": _chunk_count(artifacts["texts"]),
        "last_built_at": _utc_iso(last_built_ts),
        "variants": _list_index_variants(index_dir, system_name),
    }


def list_index_statuses(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cfg = config or load_config() or {}
    statuses = []
    for asset in get_assets(cfg):
        name = asset.get("name")
        if name:
            statuses.append(get_index_status(name, cfg))
    return statuses
