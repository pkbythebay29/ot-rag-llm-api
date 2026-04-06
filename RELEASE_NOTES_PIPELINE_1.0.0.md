# Krionis Pipeline 1.0.0

Release date: 2026-04-06

## Summary

Krionis Pipeline 1.0.0 establishes the production baseline for the local-first RAG stack. This release turns the earlier pipeline into an operator-ready platform foundation with controlled querying, mandatory human review for flagged outputs, append-only audit tracing, API-first operational controls, persisted response metadata, and a deployment path that works in regulated and airgapped settings.

## Highlights

- Quantized local model path with a smaller default LLM profile for more reliable CPU-first deployment
- Mandatory HITL gating for risky outputs with preserved original response and reviewer-edited final response
- Append-only audit events for query traces and review lifecycles
- Retrieval cache visibility and manual rebuild controls exposed through the API and built-in UX
- SQLite persistence for review queue records and result metadata such as `Good` or `Bad` ratings
- Isolated query worker process to keep the web server responsive during local model warm-up or inference failures
- Split operator UX with dedicated telemetry, runtime, configuration, and records views
- API-first controls for agent-aware controlled querying, records inspection, and runtime diagnostics
- Docker packaging for the integrated API plus orchestrator runtime
- Expanded developer and operator documentation with OpenAPI-aligned docs and deployment guidance

## What is new

### 1. Controlled query lifecycle

Every query now follows a controlled lifecycle:

`Query -> Retrieval/Generation -> HITL evaluation -> Approved output or review queue -> final traceable result`

This means the pipeline is no longer only a local RAG service. It is now an auditable controlled-query surface that can sit inside quality-sensitive workflows.

### 2. Human-in-the-loop review queue

Flagged outputs are persisted to a review queue with:

- `trace_id`
- `review_id`
- original generated response
- reviewer notes
- final approved response
- user and reviewer attribution
- timestamps

This preserves the original model output and prevents silent mutation.

### 3. Audit and traceability

Append-only audit logging now captures:

- query
- retrieved documents
- generated response
- final approved response
- reviewer decision
- timestamps
- model version
- prompt version

This creates a full query-to-output audit chain suitable for validation-heavy environments.

### 4. Persisted result metadata

Operator ratings and review outcomes are now stored in local SQLite metadata records in addition to JSONL logs. This gives teams a queryable local store for:

- `Good` ratings
- `Bad` ratings
- approved reviews
- rejected reviews

### 5. Retrieval cache administration

The pipeline now exposes retrieval cache operations through the API:

- inspect source directory
- inspect index directory
- inspect indexed files
- inspect build state
- rebuild the retrieval cache manually

This makes the knowledge-base lifecycle explicit and operable.

### 6. Quantized CPU-first runtime

The default runtime now uses:

- smaller default model: `Qwen/Qwen2.5-0.5B-Instruct`
- explicit CPU deployment mode
- dynamic int8 quantization backend
- low-memory loading safeguards

On GPU-capable systems, the runtime can still resolve back to a non-quantized path.

### 7. Isolated generation worker

Local inference now runs in an isolated worker process. If model warm-up or inference crashes, the main API server remains responsive and the failure can be inspected through runtime diagnostics.

### 8. Operator and observability pages

The built-in browser console is now split by responsibility:

- operator page
- telemetry page
- runtime page
- configuration page
- records page
- review page

The operator page keeps only the controllable workflow, while observability is separated for readability.

### 9. Docker deployment

This release adds a containerized deployment path with mounted config, data, and index volumes. That makes the integrated stack easier to start consistently across teams and environments.

### 10. Documentation and API maturity

Docs now cover:

- operator workflow
- query lifecycle
- HITL review
- deployment
- API reference
- records and observability

The platform can now be used as a frontend-agnostic backend for custom internal applications.

## Upgrade notes

- The package version is now `1.0.0`
- The default model profile changed to a smaller CPU-friendly baseline
- The platform now persists result metadata to SQLite
- The built-in UI routes expanded beyond the original landing page
- Retrieval cache management is now visible and controllable through the API

## Intended use

Krionis Pipeline 1.0.0 is intended for teams that need:

- local and airgapped RAG
- traceable AI-assisted knowledge retrieval
- controlled outputs in quality-sensitive environments
- an API surface that can support a custom frontend, portal, or validation console
