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


---

### 🔹 Krionis Orchestrator
- Microbatching & gatekeeper queue for efficient, low-latency queries.  
- Agent runtime with built-ins. 
- REST API + Web UI for monitoring and interaction.  

---

## Quickstart

### Required Setup

Before starting the orchestrator, always make sure your working directory contains:

- **`config\system.yaml`** – the main configuration file used by both the orchestrator and the pipeline.  
- **`data\manual\`** – a directory with manually curated data (shared by both the pipeline and orchestrator).

These must be present in the directory where you launch the CLI (`pwd` on Linux/macOS, current folder in Windows).

Install pipeline:

```bash
pip install krionis-pipeline
```
### Krionis Orchestrator CLI

The orchestrator ships with a cross-platform CLI, installed as `krionis-orchestrator`.  
It lets you start, stop, restart, and inspect the orchestrator.

### Basic Usage

```bash
# Start the orchestrator (detached in background)
krionis-orchestrator start --host 0.0.0.0 --port 8080

# Check if it's running
krionis-orchestrator status
# → Running (pid 12345, uptime 00:02:17).

# Stop the orchestrator
krionis-orchestrator stop

# Restart the orchestrator
krionis-orchestrator restart
```

### Options

	--host (default: 0.0.0.0) – bind address
	--port (default: 8080) – port to serve on
	--workers (default: 1) – number of uvicorn workers
	--log-file – optional path to capture logs

### Developer Mode

To run in the foreground with hot-reload (auto-restart on code changes):
```bash
krionis-orchestrator dev --host 127.0.0.1 --port 8080
```
## The CLI works the same on Linux, macOS, and Windows.

## Documentation

Krionis now includes a dedicated docs site scaffold for API consumers and platform integrators.

- Interactive API docs: `/api/docs`
- ReDoc reference: `/api/reference`
- Static docs source: `docs/`
- Docs configuration: `mkdocs.yml`
- Operator console: `/`
- Telemetry page: `/ui/telemetry`
- Runtime page: `/ui/runtime`
- Configuration page: `/ui/configuration`
- Result records page: `/ui/records`
- Reviewer dashboard: `/ui/reviews`

Build the docs site locally with:

```bash
pip install -r requirements-docs.txt
mkdocs build --strict
```

## Operator workflow

The integrated platform now exposes one operator-first flow:

1. Start an agent from the landing page.
2. Rebuild the retrieval cache when source files change.
3. Submit a controlled query through the selected agent.
4. Review flagged outputs in the review dashboard.
5. Rate outputs as `Good` or `Bad`, with the result stored in local metadata records.

All of those interactions are also available through the API, so teams can build their own frontend on top of the same contract.

## Docker

The repository now includes a containerized startup path for the integrated API plus orchestrator runtime:

```bash
docker compose up --build
```

The compose file mounts:

- `./config` to `/app/config`
- `./data` to `/app/data`
- `./indices` to `/app/indices`

So local documents, indexes, review records, audit logs, and result metadata stay outside the image.

