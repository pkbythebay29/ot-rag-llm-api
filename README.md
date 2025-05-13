# RAG-LLM-API-Pipeline

A fully  local GPU poor, multimodal Retrieval-Augmented Generation (RAG) system powered by open-source local LLMs. This pipeline is designed for operational technology environments to provide AI-assisted access to technical knowledge, manuals, and historical data — securely and offline, at min cost.

---

## ✅ Key Features

- 🔍 Retrieval-Augmented Generation (RAG) using FAISS + SentenceTransformers
- 🧠 Query handling via a local, open-source Large Language Model (LLM)
- 📄 Supports multiple input formats:
  - PDFs
  - Plain text files
  - Images (OCR via Tesseract)
  - Audio files (`.wav`, `.flac`, `.aiff`)
  - Videos (`.mp4` with audio extraction)
- 💻 Interfaces:
  - Command Line Interface (CLI)
  - Local REST API (FastAPI)
- 🛠️ Asset definition via YAML configuration
- 🔐 Works in fully local environments after setup

---

## 📂 Project Structure

```
rag_llm_api_pipeline/
├── api/                # FastAPI application
│   └── server.py
├── cli/                # Command-line interface
│   └── main.py
├── config/
│   └── system.yaml     # Asset and document config
├── data/
│   └── manuals/        # PDF, image, audio, etc.
├── loader.py           # Multimodal file loader
├── retriever.py        # Embedding, FAISS search
├── llm_wrapper.py      # Local LLM text generation
├── requirements.txt    # Python dependencies
├── README.md
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

### CLI Example
```bash
python cli/main.py --system Pump_A --question "What is the pressure threshold for operation?"
```

### API Server
Start the server:
```bash
uvicorn api.server:app --reload
```

Query with curl or Postman:
```bash
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"system": "Pump_A", "question": "Explain the restart procedure"}'
```

---

## 🧱 Configuration

Edit `config/system.yaml` to define your assets and associated documents:

```yaml
assets:
  - name: Pump_A
    docs:
      - manuals/pump_manual.pdf
      - manuals/startup_guide.png
      - manuals/technician_note.wav
```

> Documents can be PDFs, plain text, images, or audio/video files.

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
python cli/main.py --system Pump_A --question "What is the restart sequence for this machine?"
```

### API Server
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### cURL Query
```bash
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"system": "Pump_A", "question": "What does error E204 indicate?"}'
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

- Default LLM: `tiiuae/falcon-rw-1b` (run locally via `transformers`)
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- All models are open-source and run offline.

> You can replace these with any local-compatible Hugging Face model.

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