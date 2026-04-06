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
  "question": "What is the restart sequence?"
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
  "sources": ["Chunk 1"]
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

## Review queue

### `GET /review/pending`

List pending review items. Requires `x-api-key`.

### `GET /review/{review_id}`

Fetch a single review item. Requires `x-api-key`.

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

### `GET /audit/traces/{trace_id}`

Return append-only audit events for a trace. Requires `x-api-key`.

### `GET /audit/reviews/{review_id}`

Return append-only audit events for a review. Requires `x-api-key`.

## Interactive references

- Swagger UI: `/api/docs`
- ReDoc: `/api/reference`
- OpenAPI schema: `/api/openapi.json`
