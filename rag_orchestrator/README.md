# Krionis Orchestrator 1.0

Krionis Orchestrator is the agent runtime that sits on top of Krionis Pipeline. It adds agent lifecycle control, routed controlled queries, telemetry, capacity signals, and an API-first orchestration layer for teams building local AI systems in secure environments.

---

## What Is New In 1.0

- Controlled orchestrator queries routed through the same HITL and audit path as direct queries
- Agent start, stop, list, and readiness controls exposed through the API
- Capacity signaling for whether another agent can be started safely
- Dedicated telemetry and runtime diagnostics surfaces
- Frontend-agnostic lifecycle and route APIs for custom applications
- Better startup behavior by avoiding eager provider initialization
- Docker-ready deployment path when paired with Krionis Pipeline

## Core Capabilities

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
