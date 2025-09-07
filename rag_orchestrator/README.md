# Krionis Orchestrator

A lightweight orchestration runtime built on top of **Krionis Pipeline**.  
It enables **batching, multi-agent workflows, and coordination** for low-latency, multi-user RAG systems.

---

## 🤖 Key Features

⚡ **Batching & Microbatching**  
- Queueing + scheduling for efficient parallel queries  
- Smooth multi-user handling (no “stuck at starting”)  

🕹 **Agent Runtime**  
- Built-in agents: Retriever, Compressor, Reranker, Drafting, Validator, Dialogue, Coordinator  
- Agents communicate, self-optimize, and hand off state until human approval  

🔗 **Provider Plug-ins**  
- Pluggable backends (local LLMs, APIs, hybrid deployments)  
- Bridges directly to [`krionis-pipeline`](https://pypi.org/project/krionis-pipeline/)  

🌐 **API + Web Interface + CLI **  
- REST endpoints for orchestration and multi-agent queries  
- Minimal HTML UI for monitoring and interaction
- CLI interface for starting/stopping and monitoring the orchestrator   

🛡 **Resilient Runtime**  
- Timeouts, retries, and cancellation built in  
- Lightweight, works offline and in low-compute setups  

---

## Quickstart

### Required Setup

Before starting the orchestrator, always make sure your working directory contains:

- **`config\system.yaml`** – the main configuration file used by both the orchestrator and the pipeline.  
- **`data\manual\`** – a directory with manually curated data (shared by both the pipeline and orchestrator).

These must be present in the directory where you launch the CLI (`pwd` on Linux/macOS, current folder in Windows).


Install:

```bash
pip install krionis-orchestrator
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
