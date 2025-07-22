# 🚀 Quickstart: OT RAG LLM API Pipeline

This quickstart shows how to install, configure, index, and run the pipeline in minutes.

---

## 🖥️ 1️⃣ Install & setup

Clone the repo:
```bash
git clone https://github.com/pkbythebay29/ot-rag-llm-api.git
cd ot-rag-llm-api
```
Create and activate a virtual environment:
```
python3 -m venv venv
source venv/bin/activate
```
Install dependencies:
```
pip install -r requirements.txt
```
🗂️ 2️⃣ Prepare data

Put your manuals and reference files (PDFs, text, images, audio, video) into:
```
data/manuals/
```
Edit config/system.yaml to define your systems:

assets:
  - name: Pump_A
    docs: []   # leave empty to auto-discover all files

🗃️ 3️⃣ Build the index

Run:
```
rag-cli --system Pump_A --build-index
```
This creates a FAISS index in indices/.
💬 4️⃣ Ask a question
CLI:
```
rag-cli --system Pump_A --question "How do I restart the pump?"
```
With retrieved chunks:
```
rag-cli --system Pump_A --question "..." --show-chunks
```
🌐 5️⃣ Run the API server & Web UI

Start the API server:
```
rag-cli --system Pump_A --serve
```
✅ API endpoints:

    Health check: http://localhost:8000/health

    Query: POST /query with JSON:

    {
      "system": "Pump_A",
      "question": "How do I restart?"
    }

✅ Web UI:
Open browser at:
http://localhost:8000/

(if webapp/index.html exists)
🔍 6️⃣ Optional

List indexed data:
```
rag-cli --system Pump_A --list-data
```
Run with CPU:
```
rag-cli --system Pump_A --question "..." --precision fp32
```
Run with lower precision (GPU-friendly):
```
rag-cli --system Pump_A --precision fp16 --question "..."
```
📝 Notes

    Default config: config/system.yaml

    Data folder: data/manuals/

    Web UI: webapp/index.html

    Indices: indices/