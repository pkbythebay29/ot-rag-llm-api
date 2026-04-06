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

1. Start an agent from `/`
2. Confirm the source and index directories shown in the knowledge base panel
3. Rebuild the cache if you added or changed source files
4. Submit a controlled query
5. Approve or reject flagged outputs in `/ui/reviews`
6. Inspect stored ratings and review outcomes in `/ui/records`

## First API calls

```bash
curl -X POST http://127.0.0.1:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"system\":\"TestSystem\",\"question\":\"What is the restart sequence?\"}"
```

Possible outcomes:

- `approved`: the response can be returned immediately.
- `pending_review`: the response was captured for human review and includes a `review_id`.

Start an agent:

```bash
curl -X POST http://127.0.0.1:8000/platform/agents/start ^
  -H "Content-Type: application/json" ^
  -d "{\"system\":\"TestSystem\",\"agent_type\":\"retriever\",\"name_prefix\":\"agent\"}"
```

Rebuild the retrieval cache:

```bash
curl -X POST http://127.0.0.1:8000/platform/indexes/TestSystem/rebuild
```

## Docker quickstart

```bash
docker compose up --build
```

Then open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api/docs`
