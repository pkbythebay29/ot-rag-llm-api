# Authentication

## Review and audit protection

Protected endpoints require an API key in the `x-api-key` header.

The key is resolved from:

- `KRIONIS_REVIEW_API_KEY`
- or `security.api_key` in `config/system.yaml`

## Reviewer identity

Approval and rejection actions should also include:

```text
x-reviewer-id: qa-user-123
```

This supports attributable review actions in the audit trail.

## User attribution on query submission

Query callers can provide:

```text
x-user-id: operator-456
```

If omitted, Krionis falls back to `anonymous`.

## Example

```bash
curl http://127.0.0.1:8000/review/pending ^
  -H "x-api-key: your-review-key"
```
