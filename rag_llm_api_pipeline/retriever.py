# rag_llm_api_pipeline/retriever.py
import os
import time
import pickle
import faiss
from typing import Dict, Any, List

from sentence_transformers import SentenceTransformer

from rag_llm_api_pipeline.loader import load_docs
from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.llm_wrapper import ask_llm

config = load_config()
INDEX_DIR = config.get("retriever", {}).get("index_dir", "indices")


def _now():
    return time.perf_counter()


def build_index(system_name: str) -> Dict[str, Any]:
    """
    Build FAISS index and return timing report:
    {
      "total_sec": float,
      "load_parse": [{"file": str, "chunks": int, "sec": float, "error"?: str}],
      "embed_sec": float,
      "num_chunks": int,
      "index_write_sec": float
    }
    """
    os.makedirs(INDEX_DIR, exist_ok=True)
    data_dir = config["settings"]["data_dir"]
    batch_size = int(config["retriever"].get("encode_batch_size", 32))

    system = next((a for a in config["assets"] if a["name"] == system_name), None)
    docs = system.get("docs", []) if system else []
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
            parts = load_docs(full_path)  # list[str]
            texts.extend(parts)
            metas.extend([{"file": doc}] * len(parts))  # persist filename per chunk
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

    # Embeddings (batched)
    embedding_model = config["retriever"]["embedding_model"]
    embedder = SentenceTransformer(embedding_model)

    import numpy as np

    t_emb0 = _now()
    batches = []
    for i in range(0, len(texts), batch_size):
        batches.append(embedder.encode(texts[i : i + batch_size]))
    embeddings = np.vstack(batches)
    t_emb1 = _now()

    # FAISS index + persist
    t_w0 = _now()
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, os.path.join(INDEX_DIR, f"{system_name}.faiss"))
    with open(os.path.join(INDEX_DIR, f"{system_name}_texts.pkl"), "wb") as f:
        pickle.dump(texts, f)
    with open(os.path.join(INDEX_DIR, f"{system_name}_meta.pkl"), "wb") as f:
        pickle.dump(metas, f)
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
    embedding_model = config["retriever"]["embedding_model"]
    embedder = SentenceTransformer(embedding_model)

    index_path = os.path.join(INDEX_DIR, f"{system_name}.faiss")
    texts_path = os.path.join(INDEX_DIR, f"{system_name}_texts.pkl")
    meta_path = os.path.join(INDEX_DIR, f"{system_name}_meta.pkl")

    if not os.path.exists(index_path) or not os.path.exists(texts_path):
        raise RuntimeError(
            f"Missing index or texts for system '{system_name}'. Run build_index first."
        )

    index = faiss.read_index(index_path)
    with open(texts_path, "rb") as f:
        texts = pickle.load(f)  # nosec B301
    metas = []
    if os.path.exists(meta_path):
        with open(meta_path, "rb") as f:
            metas = pickle.load(f)  # nosec B301

    # Query embedding
    t_qe0 = _now()
    qv = embedder.encode([question])
    t_qe1 = _now()

    # FAISS search
    k = int(config["retriever"].get("top_k", 5))
    t_s0 = _now()
    _, index_ids = index.search(qv, k)
    t_s1 = _now()

    retrieved_idx = index_ids[0].tolist()
    chunks = [texts[i] for i in retrieved_idx]

    # Chunk metadata (with filenames if available)
    chunks_meta = []
    for r, idx in enumerate(retrieved_idx):
        item = {"rank": r + 1, "index": idx, "char_len": len(texts[idx])}
        if metas and idx < len(metas) and "file" in metas[idx]:
            item["file"] = metas[idx]["file"]
        chunks_meta.append(item)

    # Context stitch timing
    t_ctx0 = _now()
    context = "\n".join(chunks)
    t_ctx1 = _now()

    timings = {
        "embed_query_sec": round(t_qe1 - t_qe0, 4),
        "faiss_search_sec": round(t_s1 - t_s0, 4),
        "context_stitch_sec": round(t_ctx1 - t_ctx0, 4),
    }
    return chunks, context, chunks_meta, timings


def get_answer(system_name: str, question: str):
    """
    ALWAYS returns raw chunks (sources) for compatibility:
      (answer, chunks, stats)
    """
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
    Print a summary of what's indexed for a given system.
    """
    texts_path = os.path.join(INDEX_DIR, f"{system_name}_texts.pkl")
    index_path = os.path.join(INDEX_DIR, f"{system_name}.faiss")
    if not os.path.exists(texts_path) or not os.path.exists(index_path):
        print(f"[INFO] No index found for '{system_name}'. Run --build-index first.")
        return
    with open(texts_path, "rb") as f:
        texts = pickle.load(f)  # nosec B301
    print(f"[INFO] System: {system_name}")
    print(f"[INFO] Index dir: {INDEX_DIR}")
    print(f"[INFO] Chunks: {len(texts)}")
