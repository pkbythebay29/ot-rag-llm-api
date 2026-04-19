from __future__ import annotations

import os
import pickle
import time
from typing import Any

import numpy as np

from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core.model_selection import (
    embedding_index_slug,
    resolve_runtime_selection,
)
from rag_llm_api_pipeline.core.system_assets import find_asset
from rag_llm_api_pipeline.loader import load_docs

_EMBEDDERS: dict[str, Any] = {}


def _faiss():
    import faiss

    return faiss


def _sentence_transformer(model_name: str):
    from sentence_transformers import SentenceTransformer

    embedder = _EMBEDDERS.get(model_name)
    if embedder is None:
        embedder = SentenceTransformer(model_name)
        _EMBEDDERS[model_name] = embedder
    return embedder


def _now() -> float:
    return time.perf_counter()


def _artifact_paths(
    index_dir: str, system_name: str, runtime: dict[str, Any]
) -> dict[str, str]:
    suffix = embedding_index_slug(runtime)
    base = f"{system_name}--{suffix}"
    return {
        "faiss": os.path.join(index_dir, f"{base}.faiss"),
        "texts": os.path.join(index_dir, f"{base}_texts.pkl"),
        "meta": os.path.join(index_dir, f"{base}_meta.pkl"),
        "normflag": os.path.join(index_dir, f"{base}.normflag"),
        "variant": suffix,
    }


def _get_embedder(runtime: dict[str, Any]):
    return _sentence_transformer(runtime["embedding_model"])


def _maybe_normalize(vectors: np.ndarray, normalize_embeddings: bool) -> np.ndarray:
    if normalize_embeddings:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors = vectors / norms
    return vectors


def build_index(
    system_name: str, model_selection: dict[str, Any] | None = None
) -> dict[str, Any]:
    config = load_config() or {}
    runtime = resolve_runtime_selection(config, overrides=model_selection)
    index_dir = config.get("retriever", {}).get("index_dir", "indices")
    normalize_embeddings = bool(
        config.get("retriever", {}).get("normalize_embeddings", False)
    )
    os.makedirs(index_dir, exist_ok=True)

    system = find_asset(system_name, config)
    if not system:
        raise ValueError(f"System '{system_name}' not found in assets list.")

    data_dir = system.get("docs_dir") or config["settings"]["data_dir"]
    docs = system.get("docs", [])
    if not docs:
        docs = [
            name
            for name in os.listdir(data_dir)
            if os.path.isfile(os.path.join(data_dir, name))
        ]
        print(f"[INFO] Auto-discovered {len(docs)} documents in {data_dir}")

    timings: dict[str, list[Any]] = {"load_parse": []}
    total_started_at = _now()
    texts: list[str] = []
    metas: list[dict[str, Any]] = []

    for doc in docs:
        full_path = os.path.abspath(os.path.join(data_dir, doc))
        started_at = _now()
        try:
            parts = load_docs(full_path)
            texts.extend(parts)
            metas.extend([{"file": doc}] * len(parts))
            elapsed = _now() - started_at
            timings["load_parse"].append(
                {"file": doc, "chunks": len(parts), "sec": round(elapsed, 4)}
            )
        except Exception as exc:
            print(f"[WARN] Skipping '{doc}': {exc}")
            timings["load_parse"].append(
                {"file": doc, "chunks": 0, "sec": 0.0, "error": str(exc)}
            )

    if not texts:
        print("[ERROR] No text loaded from documents. Aborting index build.")
        return {"total_sec": 0.0, "error": "no_texts"}

    embedder = _get_embedder(runtime)
    batch_size = int(config["retriever"].get("encode_batch_size", 32))

    embed_started_at = _now()
    batches = []
    for offset in range(0, len(texts), batch_size):
        emb = embedder.encode(texts[offset : offset + batch_size])
        batches.append(emb)
    embeddings = np.vstack(batches)
    embeddings = _maybe_normalize(embeddings, normalize_embeddings)
    embed_finished_at = _now()

    write_started_at = _now()
    faiss = _faiss()
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    artifacts = _artifact_paths(index_dir, system_name, runtime)
    faiss.write_index(index, artifacts["faiss"])
    with open(artifacts["texts"], "wb") as handle:
        pickle.dump(texts, handle)
    with open(artifacts["meta"], "wb") as handle:
        pickle.dump(metas, handle)
    with open(artifacts["normflag"], "w", encoding="utf-8") as handle:
        handle.write("1" if normalize_embeddings else "0")
    write_finished_at = _now()

    report = {
        "total_sec": round(_now() - total_started_at, 4),
        "load_parse": timings["load_parse"],
        "embed_sec": round(embed_finished_at - embed_started_at, 4),
        "num_chunks": len(texts),
        "index_write_sec": round(write_finished_at - write_started_at, 4),
        "embedding_model": runtime["embedding_model"],
        "embedding_variant": artifacts["variant"],
        "index_files": artifacts,
    }
    print(
        f"[SUCCESS] Index built for '{system_name}' with {len(texts)} chunks "
        f"using '{runtime['embedding_model']}' in {report['total_sec']}s."
    )
    return report


def _retrieve_chunks(
    system_name: str,
    question: str,
    model_selection: dict[str, Any] | None = None,
):
    config = load_config() or {}
    runtime = resolve_runtime_selection(config, overrides=model_selection)
    index_dir = config.get("retriever", {}).get("index_dir", "indices")
    normalize_embeddings = bool(
        config.get("retriever", {}).get("normalize_embeddings", False)
    )
    embedder = _get_embedder(runtime)
    artifacts = _artifact_paths(index_dir, system_name, runtime)

    if not os.path.exists(artifacts["faiss"]) or not os.path.exists(artifacts["texts"]):
        raise RuntimeError(
            "Missing index artifacts for system "
            f"'{system_name}' and embedding model '{runtime['embedding_model']}'. "
            "Run build_index or the rebuild-index API for this embedding profile first."
        )

    faiss = _faiss()
    index = faiss.read_index(artifacts["faiss"])
    with open(artifacts["texts"], "rb") as handle:
        texts = pickle.load(handle)

    metas = []
    if os.path.exists(artifacts["meta"]):
        with open(artifacts["meta"], "rb") as handle:
            metas = pickle.load(handle)

    if os.path.exists(artifacts["normflag"]):
        with open(artifacts["normflag"], encoding="utf-8") as handle:
            stored_flag = handle.read().strip()
        if stored_flag != ("1" if normalize_embeddings else "0"):
            print(
                "[WARN] Normalization setting changed since index build. Rebuild the index."
            )

    embed_query_started_at = _now()
    query_vector = embedder.encode([question])
    query_vector = _maybe_normalize(query_vector, normalize_embeddings)
    embed_query_finished_at = _now()

    top_k = int(config["retriever"].get("top_k", 5))
    search_started_at = _now()
    _, index_ids = index.search(query_vector, top_k)
    search_finished_at = _now()

    retrieved_idx = index_ids[0].tolist()
    chunks = [texts[i] for i in retrieved_idx]
    chunks_meta = []
    for rank, idx in enumerate(retrieved_idx, start=1):
        item = {"rank": rank, "index": idx, "char_len": len(texts[idx])}
        if metas and idx < len(metas) and "file" in metas[idx]:
            item["file"] = metas[idx]["file"]
        item["embedding_model"] = runtime["embedding_model"]
        chunks_meta.append(item)

    context = "\n".join(chunks)
    timings = {
        "embed_query_sec": round(embed_query_finished_at - embed_query_started_at, 4),
        "faiss_search_sec": round(search_finished_at - search_started_at, 4),
        "context_stitch_sec": 0.0,
        "embedding_model": runtime["embedding_model"],
        "embedding_variant": artifacts["variant"],
    }
    return chunks, context, chunks_meta, timings


def get_answer(
    system_name: str,
    question: str,
    model_selection: dict[str, Any] | None = None,
):
    from rag_llm_api_pipeline.llm_wrapper import ask_llm

    started_at = _now()
    chunks, context, chunks_meta, retrieval_timings = _retrieve_chunks(
        system_name, question, model_selection=model_selection
    )
    answer, gen_stats = ask_llm(question, context, model_selection=model_selection)
    finished_at = _now()

    stats = {
        "query_time_sec": round(finished_at - started_at, 4),
        **gen_stats,
        "retrieval": retrieval_timings,
        "chunks_meta": chunks_meta,
    }
    return answer, chunks, stats


def list_indexed_data(
    system_name: str, model_selection: dict[str, Any] | None = None
) -> None:
    config = load_config() or {}
    runtime = resolve_runtime_selection(config, overrides=model_selection)
    index_dir = config.get("retriever", {}).get("index_dir", "indices")
    artifacts = _artifact_paths(index_dir, system_name, runtime)
    if not os.path.exists(artifacts["texts"]) or not os.path.exists(artifacts["faiss"]):
        print(
            f"[INFO] No index found for '{system_name}' using '{runtime['embedding_model']}'."
        )
        return

    with open(artifacts["texts"], "rb") as handle:
        texts = pickle.load(handle)
    print(f"[INFO] System: {system_name}")
    print(f"[INFO] Index dir: {index_dir}")
    print(f"[INFO] Embedding model: {runtime['embedding_model']}")
    print(f"[INFO] Chunks: {len(texts)}")
