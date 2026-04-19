# HITL Review

## Review queue capabilities

The review API supports:

- listing pending items
- fetching an individual review item
- fetching signoff-ready approval and rejection examples for a pending item
- approving an item with an optional edited final response
- rejecting an item with reviewer notes

## Approval behavior

Approval preserves:

- original generated response
- reviewer identity
- optional reviewer notes
- final approved response
- timestamps

## Rejection behavior

Rejection preserves:

- original generated response
- reviewer identity
- reviewer notes
- timestamps

Rejections are also written to the append-only audit log and the feedback dataset.

## Reviewer UI

The built-in dashboard at `/ui/reviews` supports:

- viewing pending items
- editing the final response
- entering reviewer notes
- showing the exact signoff API calls for the selected review item
- approving or rejecting in place

It is designed as an internal operations tool, while the API remains the main integration surface for external systems.

## Signoff helper

Use `GET /review/{review_id}/signoff` when you need the approval or rejection call shape generated for you.

The helper returns:

- the exact `approve` and `reject` URLs
- required headers such as `x-api-key` and `x-reviewer-id`
- example JSON payloads
- ready-to-run `curl` snippets

This is the easiest way to wire an external signoff client without manually reconstructing the review API contract.
