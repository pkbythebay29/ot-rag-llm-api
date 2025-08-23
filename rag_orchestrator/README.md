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

🌐 **API + Web Interface**  
- REST endpoints for orchestration and multi-agent queries  
- Minimal HTML UI for monitoring and interaction  

🛡 **Resilient Runtime**  
- Timeouts, retries, and cancellation built in  
- Lightweight, works offline and in low-compute setups  

---

## 🚀 Quickstart

Install:

```bash
pip install krionis-orchestrator
```