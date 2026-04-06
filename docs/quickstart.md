# Quickstart

## Local setup

Create or activate a Python environment, then install the package dependencies:

```bash
pip install -r requirements.txt
```

Set a review API key before using protected review or audit endpoints:

```bash
set KRIONIS_REVIEW_API_KEY=your-review-key
```

Start the API:

```bash
uvicorn rag_llm_api_pipeline.api.server:app --host 127.0.0.1 --port 8000
```

## First URLs to open

- Main operator UI: `http://127.0.0.1:8000/`
- Reviewer dashboard: `http://127.0.0.1:8000/ui/reviews`
- Swagger UI: `http://127.0.0.1:8000/api/docs`
- ReDoc: `http://127.0.0.1:8000/api/reference`

## First API call

```bash
curl -X POST http://127.0.0.1:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"system\":\"TestSystem\",\"question\":\"What is the restart sequence?\"}"
```

Possible outcomes:

- `approved`: the response can be returned immediately.
- `pending_review`: the response was captured for human review and includes a `review_id`.
