# rag_llm_api_pipeline/retriever.py
import os
import time
import pickle
import faiss
import numpy as np
from typing import Dict, Any, List

from sentence_transformers import SentenceTransformer
from rag_llm_api_pipeline.loader import load_docs
from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.core.system_assets import find_asset

# Global embedder cache to avoid reloading between calls
_EMBEDDER = None
_EMBEDDER_MODEL = None


def _now():
    return time.perf_counter()


def _get_embedder():
    """Lazily initialize and cache the embedding model."""
    global _EMBEDDER, _EMBEDDER_MODEL
    config = load_config() or {}
    model_name = config["retriever"]["embedding_model"]
    if _EMBEDDER is None or _EMBEDDER_MODEL != model_name:
        _EMBEDDER = SentenceTransformer(model_name)
        _EMBEDDER_MODEL = model_name
    return _EMBEDDER


def _maybe_normalize(vectors: np.ndarray, normalize_embeddings: bool) -> np.ndarray:
    """Optionally normalize embeddings to unit length (cosine-like search)."""
    if normalize_embeddings:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors = vectors / norms
    return vectors


def build_index(system_name: str) -> Dict[str, Any]:
    """
    Build FAISS index and return timing report.
    """
    config = load_config() or {}
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
            f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))
        ]
        print(f"[INFO] Auto-discovered {len(docs)} documents in {data_dir}")

    timings: dict[str, list[Any]] = {"load_parse": []}
    t_total0 = _now()

    texts: List[str] = []
    metas: List[dict] = []

    for doc in docs:
        full_path = os.path.abspath(os.path.join(data_dir, doc))
        t0 = _now()
        try:
            parts = load_docs(full_path)
            texts.extend(parts)
            metas.extend([{"file": doc}] * len(parts))
            sec = _now() - t0
            timings["load_parse"].append(
                {"file": doc, "chunks": len(parts), "sec": round(sec, 4)}
            )
        except Exception as e:
            print(f"[WARN] Skipping '{doc}': {e}")
            timings["load_parse"].append(
                {"file": doc, "chunks": 0, "sec": 0.0, "error": str(e)}
            )

    if not texts:
        print("[ERROR] No text loaded from documents. Aborting index build.")
        return {"total_sec": 0.0, "error": "no_texts"}

    # Embeddings
    embedder = _get_embedder()
    batch_size = int(config["retriever"].get("encode_batch_size", 32))

    t_emb0 = _now()
    batches = []
    for i in range(0, len(texts), batch_size):
        emb = embedder.encode(texts[i : i + batch_size])
        batches.append(emb)
    embeddings = np.vstack(batches)
    embeddings = _maybe_normalize(embeddings, normalize_embeddings)
    t_emb1 = _now()

    # Build FAISS index
    t_w0 = _now()
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, os.path.join(index_dir, f"{system_name}.faiss"))
    with open(os.path.join(index_dir, f"{system_name}_texts.pkl"), "wb") as handle:
        pickle.dump(texts, handle)
    with open(os.path.join(index_dir, f"{system_name}_meta.pkl"), "wb") as handle:
        pickle.dump(metas, handle)
    with open(
        os.path.join(index_dir, f"{system_name}.normflag"), "w", encoding="utf-8"
    ) as handle:
        handle.write("1" if normalize_embeddings else "0")
    t_w1 = _now()

    report = {
        "total_sec": round(_now() - t_total0, 4),
        "load_parse": timings["load_parse"],
        "embed_sec": round(t_emb1 - t_emb0, 4),
        "num_chunks": len(texts),
        "index_write_sec": round(t_w1 - t_w0, 4),
    }
    print(
        f"[SUCCESS] Index built for '{system_name}' with {len(texts)} chunks "
        f"in {report['total_sec']}s (embed {report['embed_sec']}s)."
    )
    return report


def _retrieve_chunks(system_name: str, question: str):
    config = load_config() or {}
    index_dir = config.get("retriever", {}).get("index_dir", "indices")
    normalize_embeddings = bool(
        config.get("retriever", {}).get("normalize_embeddings", False)
    )
    embedder = _get_embedder()

    index_path = os.path.join(index_dir, f"{system_name}.faiss")
    texts_path = os.path.join(index_dir, f"{system_name}_texts.pkl")
    meta_path = os.path.join(index_dir, f"{system_name}_meta.pkl")
    normflag_path = os.path.join(index_dir, f"{system_name}.normflag")

    if not os.path.exists(index_path) or not os.path.exists(texts_path):
        raise RuntimeError(
            f"Missing index or texts for system '{system_name}'. Run build_index first."
        )

    index = faiss.read_index(index_path)
    with open(texts_path, "rb") as f:
        texts = pickle.load(f)
    metas = []
    if os.path.exists(meta_path):
        with open(meta_path, "rb") as f:
            metas = pickle.load(f)

    # Validate normalization consistency
    if os.path.exists(normflag_path):
        with open(normflag_path, encoding="utf-8") as handle:
            stored_flag = handle.read().strip()
        if stored_flag != ("1" if normalize_embeddings else "0"):
            print(
                "[WARN] Normalization setting has changed since index build. Rebuild the index."
            )

    # Query embedding
    t_qe0 = _now()
    qv = embedder.encode([question])
    qv = _maybe_normalize(qv, normalize_embeddings)
    t_qe1 = _now()

    # FAISS search
    k = int(config["retriever"].get("top_k", 5))
    t_s0 = _now()
    _, index_ids = index.search(qv, k)
    t_s1 = _now()

    retrieved_idx = index_ids[0].tolist()
    chunks = [texts[i] for i in retrieved_idx]

    chunks_meta = []
    for r, idx in enumerate(retrieved_idx):
        item = {"rank": r + 1, "index": idx, "char_len": len(texts[idx])}
        if metas and idx < len(metas) and "file" in metas[idx]:
            item["file"] = metas[idx]["file"]
        chunks_meta.append(item)

    context = "\n".join(chunks)

    timings = {
        "embed_query_sec": round(t_qe1 - t_qe0, 4),
        "faiss_search_sec": round(t_s1 - t_s0, 4),
        "context_stitch_sec": 0.0,
    }
    return chunks, context, chunks_meta, timings


def get_answer(system_name: str, question: str):
    """
    Returns (answer, chunks, stats)
    """
    from rag_llm_api_pipeline.llm_wrapper import ask_llm

    t0 = _now()
    chunks, context, chunks_meta, rt = _retrieve_chunks(system_name, question)
    answer, gen_stats = ask_llm(question, context)
    t1 = _now()

    stats = {
        "query_time_sec": round(t1 - t0, 4),
        **gen_stats,
        "retrieval": rt,
        "chunks_meta": chunks_meta,
    }
    return answer, chunks, stats


def list_indexed_data(system_name: str):
    """
    Summarize what's indexed for a given system.
    """
    config = load_config() or {}
    index_dir = config.get("retriever", {}).get("index_dir", "indices")
    texts_path = os.path.join(index_dir, f"{system_name}_texts.pkl")
    index_path = os.path.join(index_dir, f"{system_name}.faiss")
    if not os.path.exists(texts_path) or not os.path.exists(index_path):
        print(f"[INFO] No index found for '{system_name}'. Run --build-index first.")
        return
    with open(texts_path, "rb") as f:
        texts = pickle.load(f)
    print(f"[INFO] System: {system_name}")
    print(f"[INFO] Index dir: {index_dir}")
    print(f"[INFO] Chunks: {len(texts)}")
