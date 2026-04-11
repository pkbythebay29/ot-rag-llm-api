# Operator Console

## Built-in pages

Krionis ships with a browser console that is entirely API driven. The built-in UI is meant to be an operator reference implementation, not a private backend.

- `/` for the operator workflow
- `/ui/telemetry` for queue and route telemetry
- `/ui/runtime` for runtime diagnostics
- `/ui/configuration` for YAML-backed configuration visibility
- `/ui/records` for locally persisted result metadata
- `/ui/reviews` for reviewer signoff

## Operator page

The landing page keeps only the controllable workflow:

- start an agent
- switch the active model profile
- stop an agent
- select which active agent receives the next query
- rebuild the retrieval cache
- submit a controlled query
- rate the output as `Good` or `Bad`

## Why the pages are split

The operator workflow is intentionally separated from observability and configuration so the primary console stays readable during live work:

- operator actions stay on the landing page
- telemetry is isolated on its own page with a configurable refresh interval
- runtime and logs are isolated on their own page
- configuration is isolated on its own page
- result metadata is isolated on its own page

## Source directories and index cache

The console exposes where the RAG retriever is reading files from and where the retrieval cache is stored:

- source directory: the configured manual or document directory
- index directory: the FAISS and metadata cache directory

This allows operators to add new files, then rebuild the cache from either the UI or the API.

## Model profiles

Krionis exposes named model profiles through the same API-first console surface:

- `GET /platform/models` lists the available profiles
- `POST /platform/models/apply` persists the chosen profile into YAML
- `POST /platform/models/reload` resets only the isolated query worker

This keeps model swapping simple for operators while still preserving the YAML-backed runtime contract for custom frontends and deployment automation.
