# Krionis Pipeline 1.0

Krionis Pipeline is a local-first Retrieval-Augmented Generation platform for controlled, auditable AI workflows. It is designed for secure and airgapped environments where teams need API-driven retrieval, human review controls, traceability, and a practical operator experience without depending on cloud infrastructure.

Backward compatibility is preserved:

- `import rag_llm_api_pipeline` still works
- `rag-cli` still works
- `krionis-cli` is available as the branded CLI entry point

## What Is New In 1.0

- Mandatory HITL gating for flagged outputs
- Review queue persistence with original and final responses stored separately
- Append-only audit tracing across query, retrieval, generation, and signoff
- SQLite-backed result metadata for `Good` and `Bad` feedback plus review outcomes
- API-driven index visibility and manual cache rebuild operations
- Split operator UX for control, telemetry, runtime, configuration, records, and review
- CPU-friendly quantized default model profile for local deployment
- Isolated generation worker to keep the API responsive during model load or failure
- Docker packaging for integrated platform deployment
- Expanded API documentation for custom frontend development

## Core Capabilities

🔍 **Retrieval-Augmented Generation (RAG)**  
- FAISS/HNSW vector indices  
- SentenceTransformers embeddings  

🧠 **Flexible LLM Integration**  
- HuggingFace open-source models (Qwen, Mistral, LLaMA, etc.)  
- Mixed precision: fp32, fp16, bfloat16  
- Dynamic model/device/precision switching via YAML  

🔧 **1-line YAML Configuration**  
- System-specific documents  
- Embedding & generation model selection  
- CPU/GPU inference toggle  
- Index rebuilding, token limits, chunking  

📂 **Multimodal Input Support**  
- PDFs  
- Plain text  
- Images (OCR via Tesseract)  
- Audio (.wav)  
- Video (.mp4)  

💻 **Multiple Interfaces**  
- CLI (`rag-cli` / `krionis-cli`) for single-line querying  
- FastAPI-powered REST API for local serving  
- Lightweight HTML Web UI for interactive search  

---

## Quickstart

### Required Setup

Before starting the platform, make sure your working directory contains:

- `config/system.yaml`
- `data/manuals/`

Install:

```bash
pip install krionis-pipeline
```

Build the retrieval index and start the API:

```bash
krionis-cli build-index --system TestSystem
uvicorn rag_llm_api_pipeline.api.server:app --host 127.0.0.1 --port 8000
```

Open:

- `http://127.0.0.1:8000/` for the operator console
- `http://127.0.0.1:8000/api/docs` for the API reference
- `http://127.0.0.1:8000/ui/reviews` for the review queue

## Installation

```bash
pip install krionis-pipeline
```

---

## 🛠️ Setup Instructions (Windows + Anaconda)

### 1. Create Python Environment
```bash
conda create -n rag_env python=3.10
conda activate rag_env
```

### 2. Install Dependencies
#### Via Conda (system-level tools):
```bash
conda install -c conda-forge ffmpeg pytesseract pyaudio
```

#### Via Pip (Python packages):
```bash
pip install -r requirements.txt
```

> Ensure Tesseract is installed and in your system PATH. You can get it from https://github.com/tesseract-ocr/tesseract.

---

## 🚀 Usage

Please review the quickstart guide. 

---
## 🐧 Setup Instructions (Linux)

### 1. Create Python Environment
```bash
python3 -m venv rag_env
source rag_env/bin/activate
```

Or with `conda`:
```bash
conda create -n rag_env python=3.10
conda activate rag_env
```

### 2. Install System Dependencies
```bash
sudo apt update
sudo apt install -y ffmpeg tesseract-ocr libpulse-dev portaudio19-dev
```

> Optional: install language packs for OCR (e.g., `tesseract-ocr-eng`).

### 3. Install Python Packages
```bash
pip install -r requirements.txt
```

---

## 🔁 Running the Application on Linux

### CLI
```bash
python cli/main.py --system TestSystem --question "What is the restart sequence for this machine?"
```

### API Server
```bash
uvicorn rag_llm_api_pipeline.api.server:app --host 0.0.0.0 --port 8000
```

### cURL Query

```bash```
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"system": "TestSystem", "question": "What does error E204 indicate?"}'
```

## 📚 How it Works

1. **Index Building**:
   - Files are parsed using `loader.py`.
   - Text chunks are embedded with MiniLM.
   - FAISS index stores embeddings for fast similarity search.

2. **Query Execution**:
   - User provides a natural language question.
   - Relevant text chunks are retrieved from the index.
   - LLM generates an answer based on retrieved context.

---

## 🧠 Model Info

- All models are open-source and run offline.

> You can replace with any local-compatible Hugging Face model.

---

## 🔐 Security & Offline Use

- No cloud or external dependencies required after initial setup.
- Ideal for OT environments.
- All processing is local: embeddings, LLM inference, and data storage.

---

## 📜 License

MIT License

---

## 📧 Contact

For issues, improvements, or contributions, please open an issue or PR.

## Documentation

The repository includes a documentation portal scaffold for developers building on top of the Krionis API.

- Interactive API docs: `/api/docs`
- ReDoc reference: `/api/reference`
- Static docs source: `docs/`
- Docs build config: `mkdocs.yml`
