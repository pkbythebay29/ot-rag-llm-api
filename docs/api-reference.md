# API Reference

## Health

### `GET /health`

Returns service readiness.

Example response:

```json
{
  "status": "ok"
}
```

## Query

### `POST /query`

Submit a Krionis query through the orchestrator hook and HITL gate.

Request body:

```json
{
  "system": "TestSystem",
  "question": "What is the restart sequence?",
  "runtime_profile": "shared-compact",
  "inference_model": "qwen-0.5b-instruct",
  "embedding_model": "minilm-l6"
}
```

Approved response example:

```json
{
  "status": "approved",
  "trace_id": "4c31d2d7-3d7d-4d39-9f79-cf4c57c1b182",
  "system": "TestSystem",
  "question": "What is the restart sequence?",
  "answer": "The restart sequence begins by isolating the power source.",
  "sources": ["Chunk 1"],
  "runtime": {
    "runtime_profile": "shared-compact",
    "inference_model": "Qwen/Qwen2.5-0.5B-Instruct",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
  }
}
```

Pending review response example:

```json
{
  "status": "pending_review",
  "trace_id": "5d31d2d7-3d7d-4d39-9f79-cf4c57c1b183",
  "review_id": "9a4f4b6d-c6b8-47af-88c6-5d1dfd0984aa",
  "system": "TestSystem",
  "question": "What is the dosage recommendation?",
  "response_preview": "Dosage guidance requires human validation before release."
}
```

### `POST /orchestrator/query`

Submit a controlled query through a selected agent task.

Request body:

```json
{
  "task_id": "agent1-retriever-0",
  "system": "TestSystem",
  "question": "What is the restart sequence?",
  "context": "",
  "runtime_profile": "balanced-search"
}
```

## Review queue

### `GET /review/pending`

List pending review items. Requires `x-api-key`.

### `GET /review/{review_id}`

Fetch a single review item. Requires `x-api-key`.

### `GET /review/{review_id}/signoff`

Fetch ready-to-run approval and rejection examples, including URLs, headers, JSON bodies, and cURL snippets. Requires `x-api-key`.

### `POST /review/{review_id}/approve`

Approve a pending item. Requires `x-api-key`.

Request body:

```json
{
  "final_response": "Approved and verified dosage response.",
  "reviewer_notes": "Cross-checked against SOP-17."
}
```

### `POST /review/{review_id}/reject`

Reject a pending item. Requires `x-api-key`.

Request body:

```json
{
  "reviewer_notes": "Insufficient evidence for release."
}
```

## Audit and metadata

### `GET /system/metadata`

Return Krionis system metadata, platform versioning, and module classification.

### `GET /platform/configuration`

Return the active YAML-backed configuration snapshot, resolved runtime choices, and local storage paths.

### `GET /platform/dashboard`

Return the operator dashboard snapshot, including active agents, retrieval index status, recent routes, and runtime summaries.

### `GET /platform/telemetry`

Return live telemetry, recent route events, and the configured refresh interval.

### `GET /platform/runtime`

Return process-level runtime diagnostics, worker state, and recent log lines.

### `GET /platform/indexes`

Return source directories, source files, index directories, and cache state for all configured systems.

### `GET /platform/indexes/{system_name}`

Return source and cache state for one configured system.

### `POST /platform/indexes/{system_name}/rebuild`

Rebuild the retrieval cache for a system in an isolated worker. You can optionally provide `runtime_profile` or `embedding_model` in the request body so Krionis builds the matching embedding-specific cache.

### `GET /platform/models`

Return the available default inference profiles, Hugging Face inference catalog, embedding catalog, agent runtime profiles, and the currently resolved runtime selection.

### `GET /platform/agents`

List active agents and current capacity.

### `POST /platform/agents/start`

Start one built-in agent and return its task identifier.

Request body:

```json
{
  "system": "TestSystem",
  "agent_type": "retriever",
  "name_prefix": "agent",
  "tenant": "default",
  "runtime_profile": "balanced-search",
  "inference_model": "qwen-1.5b-instruct",
  "embedding_model": "bge-small-en-v1.5"
}
```

### `DELETE /platform/agents/{agent_ref}`

Stop an active agent by task name or handle ID.

### `GET /platform/routes/recent`

Return recent controlled-query routing events, including the agent used for each query.

### `GET /platform/records`

Return recent persisted result metadata, including `Good` or `Bad` ratings and review decisions.

### `GET /audit/traces/{trace_id}`

Return append-only audit events for a trace. Requires `x-api-key`.

### `GET /audit/reviews/{review_id}`

Return append-only audit events for a review. Requires `x-api-key`.

## Interactive references

- Swagger UI: `/api/docs`
- ReDoc: `/api/reference`
- OpenAPI schema: `/api/openapi.json`
