# RAG-LLM-API-Pipeline

A fully  local GPU poor, multimodal Retrieval-Augmented Generation (RAG) system powered by open-source local LLMs. This pipeline is designed for operational technology environments to provide AI-assisted access to technical knowledge, manuals, and historical data — securely and offline, at min cost.

---

✅ Key Features

    🔍 Retrieval-Augmented Generation (RAG) using FAISS + SentenceTransformers

    🧠 Flexible LLM Integration with support for:

        Open-source HuggingFace models (Qwen, Mistral, etc.)

        Mixed precision support: fp32, fp16, bfloat16

        Dynamic model/device/precision switching via YAML

    🔧 1-line YAML configuration to control:

        System-specific documents

        Embedding & generation models

        GPU/CPU inference toggle

        Index rebuilding, token limits, chunking

    📂 Multimodal Input Support:

        PDFs

        Plain text

        Images (OCR via Tesseract)

        Audio (.wav, .flac, .aiff)

        Video (.mp4 with automatic scene/audio splitting)

    💻 Multiple Interfaces:

        CLI (rag-cli) for single-line querying

        FastAPI-powered REST API for local serving

        Lightweight HTML Web UI for interactive search

    🛠️ Per-system configuration via system.yaml for flexible deployments

    🔐 Fully local operation — no cloud dependencies required

✅ One-line install via pip install rag-llm-api-pipeline
✅ Quickstart guide and prebuilt example included
✅ Runs on CPU or GPU with smart memory management
✅ Web UI + CLI + API, all in one package

---

## 📦 Installation

```bash
pip install rag-llm-api-pipeline

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
```bash
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