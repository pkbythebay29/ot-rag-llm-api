# Audit and Traceability

## Audit model

Krionis writes append-only JSONL audit events. Each event includes platform metadata and request-specific context such as:

- query
- retrieved documents
- generated response
- final approved response
- reviewer decision
- user and reviewer IDs
- timestamps
- model and prompt versions
- execution trace

## Access patterns

The API exposes audit retrieval through:

- `GET /audit/traces/{trace_id}`
- `GET /audit/reviews/{review_id}`

## Trace IDs

Every query returns a `trace_id`. External systems should persist this value so they can:

- reconstruct the lifecycle of a single query
- link application records back to Krionis execution evidence
- retrieve audit events later for investigations or inspections

## Review IDs

Flagged responses also return a `review_id`. This is the canonical handle for:

- reviewer queues
- approval or rejection actions
- review-specific audit retrieval

## ALCOA+ alignment

The platform is structured around:

- Attributable: user and reviewer identifiers
- Legible: structured JSON records
- Contemporaneous: generated timestamps
- Original: raw generated response preserved
- Accurate: no silent mutation of the original answer
