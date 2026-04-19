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
- Telemetry UI: `http://127.0.0.1:8000/ui/telemetry`
- Runtime UI: `http://127.0.0.1:8000/ui/runtime`
- Configuration UI: `http://127.0.0.1:8000/ui/configuration`
- Records UI: `http://127.0.0.1:8000/ui/records`
- Reviewer dashboard: `http://127.0.0.1:8000/ui/reviews`
- Swagger UI: `http://127.0.0.1:8000/api/docs`
- ReDoc: `http://127.0.0.1:8000/api/reference`

## First operator steps

1. Apply a default inference profile from `/ui/configuration` if the packaged fallback is not what you want.
2. Start an agent from `/` with either:
   - a named runtime profile, or
   - an explicit inference model and embedding model
2. Confirm the source and index directories shown in the knowledge base panel
3. Rebuild the cache for the embedding model that agent will use if you added or changed source files
4. Submit a controlled query
5. Approve or reject flagged outputs in `/ui/reviews`
6. Use `GET /review/{review_id}/signoff` if you want ready-made approval/rejection API examples
7. Inspect stored ratings and review outcomes in `/ui/records`

## First API calls

```bash
curl -X POST http://127.0.0.1:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"system\":\"TestSystem\",\"question\":\"What is the restart sequence?\",\"runtime_profile\":\"shared-compact\"}"
```

Possible outcomes:

- `approved`: the response can be returned immediately.
- `pending_review`: the response was captured for human review and includes a `review_id`.

Start an agent:

```bash
curl -X POST http://127.0.0.1:8000/platform/agents/start ^
  -H "Content-Type: application/json" ^
  -d "{\"system\":\"TestSystem\",\"agent_type\":\"retriever\",\"name_prefix\":\"agent\",\"runtime_profile\":\"balanced-search\",\"inference_model\":\"qwen-1.5b-instruct\",\"embedding_model\":\"bge-small-en-v1.5\"}"
```

Rebuild the retrieval cache:

```bash
curl -X POST http://127.0.0.1:8000/platform/indexes/TestSystem/rebuild ^
  -H "Content-Type: application/json" ^
  -d "{\"runtime_profile\":\"balanced-search\",\"embedding_model\":\"bge-small-en-v1.5\"}"
```

Fetch signoff examples for a pending review:

```bash
curl http://127.0.0.1:8000/review/{review_id}/signoff ^
  -H "x-api-key: your-review-key"
```

## Docker quickstart

```bash
docker compose up --build
```

Then open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api/docs`
