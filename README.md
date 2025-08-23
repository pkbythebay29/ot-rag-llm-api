# Krionis — The Local AI Knowledge Engine with Agents at its Core

**Krionis** is a fully local, GPU-poor, multimodal **Retrieval-Augmented Generation (RAG)** ecosystem built for **local-first environments — from enterprise knowledge bases to operational technology systems**.  
It provides AI-assisted access to technical knowledge, manuals, and historical data — securely, offline, and at minimal cost.

This monorepo contains **two independently published PyPI packages**:

| Package | PyPI | Description |
|---------|------|-------------|
| [`krionis-pipeline`](https://pypi.org/project/krionis-pipeline/) | Core multimodal RAG pipeline (retrieval, rerank, compression, generation). |
| [`krionis-orchestrator`](https://pypi.org/project/krionis-orchestrator/) | Orchestration runtime for batching, multi-agent workflows, and coordination. |
| [`rag-llm-api-pipeline`](https://pypi.org/project/rag-llm-api-pipeline/) | Compatibility shim that depends on `krionis-pipeline` (imports still work). |

---

## ✨ Why Krionis?

- **Local-first**: Designed for CPU/GPU-poor environments.  
- **Secure**: Air-gapped operation, no external dependencies once models are downloaded.  
- **Modular**: Pipeline provides core RAG functions; Orchestrator adds agent runtime + batching.  
- **Compatible**: Old imports (`import rag_llm_api_pipeline`) and CLI (`rag-cli`) still work.  

---

## 📦 Components

### 🔹 Krionis Pipeline
- Vector search with FAISS/HNSW + SentenceTransformers embeddings.  
- HuggingFace LLM integration (Qwen, Mistral, LLaMA, etc.).  
- Mixed precision (fp32, fp16, bfloat16) with YAML-based device/precision switching.  
- Multimodal input: text, PDFs, images (OCR), audio, video.  
- Interfaces:  
  - CLI (`rag-cli`, `krionis-cli`)  
  - FastAPI REST API  
  - Lightweight Web UI  

➡️ [See `krionis-pipeline` docs](krionis-pipeline/README.md)  

---

### 🔹 Krionis Orchestrator
- Microbatching & gatekeeper queue for efficient, low-latency queries.  
- Agent runtime with built-ins. 
- REST API + Web UI for monitoring and interaction.  


➡️ [See `krionis-orchestrator` docs](krionis-orchestrator/README.md)  

---

## 🚀 Quickstart

Install pipeline:

```bash
pip install krionis-pipeline
