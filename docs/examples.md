# Integration Examples

## Submit a query from Python

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/query",
    json={
        "system": "TestSystem",
        "question": "What is the restart sequence?",
    },
    headers={"x-user-id": "app-user-1"},
    timeout=30,
)

payload = response.json()
print(payload["status"], payload["trace_id"])
```

## Handle pending review

```python
if payload["status"] == "pending_review":
    review_id = payload["review_id"]
    print("Route this item to human review:", review_id)
```

## Pull audit events

```python
trace = requests.get(
    f"http://127.0.0.1:8000/audit/traces/{payload['trace_id']}",
    headers={"x-api-key": "your-review-key"},
    timeout=30,
)
print(trace.json())
```

## Approve a review item

```python
approved = requests.post(
    f"http://127.0.0.1:8000/review/{review_id}/approve",
    headers={
        "x-api-key": "your-review-key",
        "x-reviewer-id": "qa-1",
    },
    json={
        "final_response": "Approved and verified dosage response.",
        "reviewer_notes": "Reviewed by QA.",
    },
    timeout=30,
)
print(approved.json()["status"])
```
