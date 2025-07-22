import os, pickle
from rag_llm_api_pipeline.loader import load_documents
from rag_llm_api_pipeline.config_loader import load_config
from rag_llm_api_pipeline.llm_wrapper import ask_llm

from sentence_transformers import SentenceTransformer
import faiss

INDEX_DIR = "indices"
config = load_config()

def build_index(system_name):
    os.makedirs(INDEX_DIR, exist_ok=True)
    data_dir = config["settings"]["data_dir"]
    system = next((a for a in config["assets"] if a["name"] == system_name), None)
    docs = system.get("docs") if system else None

    if not docs:
        docs = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]

    texts = load_documents([os.path.abspath(os.path.join(data_dir, doc)) for doc in docs])
    embedder = SentenceTransformer(config["retriever"]["embedding_model"])
    embeddings = embedder.encode(texts)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, os.path.join(INDEX_DIR, f"{system_name}.faiss"))

    with open(os.path.join(INDEX_DIR, f"{system_name}_texts.pkl"), "wb") as f:
        pickle.dump(texts, f)

def get_answer(system_name, question):
    embedder = SentenceTransformer(config["retriever"]["embedding_model"])
    index = faiss.read_index(os.path.join(INDEX_DIR, f"{system_name}.faiss"))
    with open(os.path.join(INDEX_DIR, f"{system_name}_texts.pkl"), "rb") as f:
        texts = pickle.load(f)

    question_vec = embedder.encode([question])
    D, I = index.search(question_vec, config["retriever"]["top_k"])
    context = "\n".join([texts[i] for i in I[0]])
    answer = ask_llm(question, context)
    return answer, [texts[i] for i in I[0]]

def list_indexed_data(system_name):
    meta_path = os.path.join(INDEX_DIR, f"{system_name}_texts.pkl")
    if not os.path.exists(meta_path):
        print(f"No index found for {system_name}")
        return
    with open(meta_path, "rb") as f:
        texts = pickle.load(f)
    print(f"Indexed {len(texts)} chunks for system: {system_name}")
