# Krionis Orchestrator 1.0.0

Release date: 2026-04-06

## Summary

Krionis Orchestrator 1.0.0 marks the first production baseline for the agent runtime that sits on top of Krionis Pipeline. This release moves the orchestrator from an early runtime into an operational coordination layer that can start agents, route controlled queries, expose live telemetry, and integrate directly into the HITL and audit surfaces of the platform.

## Highlights

- Stable 1.0 agent runtime baseline
- Integrated agent lifecycle controls exposed through the main platform API
- Controlled orchestrator query path routed through the same HITL and audit controls as direct queries
- Restored active-agent visibility and queue telemetry in the integrated platform
- Agent readiness and selection surfaced for operators and external frontends
- Agent stop and start controls exposed through public API routes
- Capacity and resource headroom surfaced to determine whether another agent can be started
- Runtime and telemetry views now separated from the landing operator workflow
- Better startup behavior by removing eager provider loading during agent start
- Docker-ready packaging with the orchestrator installed into the same integrated image

## What is new

### 1. Controlled agent queries

Queries routed through orchestrator agents now flow through the same controlled-query path as direct API queries. This ensures:

- consistent HITL behavior
- consistent trace IDs
- consistent review handling
- consistent audit capture

### 2. Agent lifecycle visibility

Active agents are now visible through the platform API and the built-in UI, including:

- task identifier
- name
- system binding
- type
- readiness

### 3. Agent start and stop controls

External clients and the built-in UI can now:

- start agents
- stop agents
- list agents
- select which active agent receives the next controlled query

### 4. Better startup behavior

Agent start no longer eagerly triggers heavy model/provider initialization. This keeps the operator workflow lighter and avoids misleading startup failures.

### 5. Capacity signaling

The platform now exposes resource-based capacity hints that tell the operator whether another agent can be started safely based on current memory and CPU headroom.

### 6. Integrated telemetry

Microbatch and queue telemetry are now visible through both dedicated telemetry APIs and the built-in telemetry page. This makes orchestration behavior inspectable without custom code.

### 7. Runtime diagnostics

The integrated runtime page now exposes:

- process uptime
- process memory
- free system memory
- CPU usage
- worker state
- recent runtime logs

### 8. Frontend-agnostic orchestration surface

The orchestrator is now easier to embed into a custom frontend because lifecycle, telemetry, and recent-route information are exposed through stable platform APIs instead of only the built-in web UI.

### 9. Coordination with pipeline records

Recent routed queries are now persisted as route events in memory for dashboard use, while review and rating outcomes persist into the platform metadata store for later inspection.

### 10. Release alignment

This 1.0 release aligns the orchestrator with the integrated platform baseline, documentation, and deployment story so teams can adopt both packages as a single coherent local AI stack.

## Upgrade notes

- The package version is now `1.0.0`
- The FastAPI app version is now `1.0.0`
- Agent lifecycle is now surfaced through the integrated platform API
- Orchestrated queries now inherit the same controlled-query behavior as direct queries

## Intended use

Krionis Orchestrator 1.0.0 is intended for teams that need:

- multi-agent local AI coordination
- visible queue and batching behavior
- agent-aware routing under HITL constraints
- a scalable orchestration layer on top of a local, regulated RAG platform
