# Query Lifecycle

## End-to-end flow

Krionis processes requests through a controlled execution path:

1. Query received
2. Orchestrator hook invoked
3. Document search tool runs the existing RAG pipeline
4. HITL policy evaluates the generated response
5. The system either returns `approved` or writes a `pending_review` item
6. Audit records are appended for downstream traceability

## Approved path

When a response is not flagged, the API returns:

- `status`
- `trace_id`
- `system`
- `question`
- `answer`
- `sources`
- optional `stats`

## Pending review path

When a response is flagged, the API returns:

- `status = pending_review`
- `trace_id`
- `review_id`
- `system`
- `question`
- `response_preview`
- optional `stats`

The original generated response is preserved in the review store and never silently overwritten.

## Why a query is flagged

The default HITL policy currently flags responses when:

- the query or response contains one of the review keywords
- the generated response exceeds the configured length threshold

Default keywords:

- dosage
- treatment
- compliance
- gmp
- validation
