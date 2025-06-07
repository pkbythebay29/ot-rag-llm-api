# RAG retrieval logic
import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer
from .loader import load_docs
from .llm_wrapper import ask_llm
from .config_loader import load_config

config = load_config()
embedding_model = SentenceTransformer(config["models"]["embedding_model"])
INDEX_DIR = config["retriever"]["index_dir"]
os.makedirs(INDEX_DIR, exist_ok=True)

def build_index(system_name: str, docs: list[str]) -> str:
    texts = []
    for doc_path in docs:
        full_path = os.path.join(config["settings"]["data_dir"], doc_path)
        texts.extend(load_docs(full_path))

    embeddings = embedding_model.encode(texts, show_progress_bar=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    index_path = os.path.join(INDEX_DIR, f"{system_name}.faiss")
    meta_path = os.path.join(INDEX_DIR, f"{system_name}_texts.pkl")

    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(texts, f)

    return index_path

def get_answer(system_name: str, question: str) -> tuple[str, list[str]]:
    index_path = os.path.join(INDEX_DIR, f"{system_name}.faiss")
    meta_path = os.path.join(INDEX_DIR, f"{system_name}_texts.pkl")

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        raise ValueError(f"Index for system '{system_name}' not found. Please build it first.")

    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        texts = pickle.load(f)

    question_embedding = embedding_model.encode([question])
    D, I = index.search(question_embedding, k=config["retriever"]["top_k"])
    top_chunks = [texts[i] for i in I[0]]

    context = "\n\n".join(top_chunks)
    answer = ask_llm(question=question, context=context)

    return answer, top_chunks
