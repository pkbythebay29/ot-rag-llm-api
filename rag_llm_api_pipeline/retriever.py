import os
import pickle
from rag_llm_api_pipeline.loader import load_docs
from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.llm_wrapper import ask_llm

from sentence_transformers import SentenceTransformer
import faiss

INDEX_DIR = "indices"
config = load_config()

def build_index(system_name):
    os.makedirs(INDEX_DIR, exist_ok=True)
    data_dir = config["settings"]["data_dir"]

    # Get the system's document list
    system = next((a for a in config["assets"] if a["name"] == system_name), None)
    docs = system.get("docs") if system else None

    # Fallback: use all files in data_dir
    if not docs:
        docs = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]

    # Load and combine text from all supported documents
    texts = []
    for doc in docs:
        path = os.path.abspath(os.path.join(data_dir, doc))
        try:
            texts.extend(load_docs(path))
        except Exception as e:
            print(f"[WARN] Failed to load '{path}': {e}")

    if not texts:
        print("[ERROR] No text could be loaded. Aborting index build.")
        return

    # Create embedding and index
    embedding_model = config["retriever"]["embedding_model"]
    embedder = SentenceTransformer(embedding_model)
    embeddings = embedder.encode(texts)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, os.path.join(INDEX_DIR, f"{system_name}.faiss"))

    # Save text chunks
    with open(os.path.join(INDEX_DIR, f"{system_name}_texts.pkl"), "wb") as f:
        pickle.dump(texts, f)

    print(f"[INFO] Index built and saved for '{system_name}' with {len(texts)} text chunks.")

def get_answer(system_name, question):
    embedding_model = config["retriever"]["embedding_model"]
    embedder = SentenceTransformer(embedding_model)

    index_path = os.path.join(INDEX_DIR, f"{system_name}.faiss")
    texts_path = os.path.join(INDEX_DIR, f"{system_name}_texts.pkl")

    if not os.path.exists(index_path) or not os.path.exists(texts_path):
        print(f"[ERROR] Missing index or text data for system '{system_name}'. Run build_index first.")
        return None, []

    index = faiss.read_index(index_path)
    with open(texts_path, "rb") as f:
        texts = pickle.load(f)

    question_vec = embedder.encode([question])
    D, I = index.search(question_vec, config["retriever"]["top_k"])
    context_chunks = [texts[i] for i in I[0]]
    context = "\n".join(context_chunks)

    answer = ask_llm(question, context)
    return answer, context_chunks

def list_indexed_data(system_name):
    meta_path = os.path.join(INDEX_DIR, f"{system_name}_texts.pkl")
    if not os.path.exists(meta_path):
        print(f"No index found for {system_name}")
        return

    with open(meta_path, "rb") as f:
        texts = pickle.load(f)

    print(f"[INFO] Indexed {len(texts)} chunks for system: {system_name}")
