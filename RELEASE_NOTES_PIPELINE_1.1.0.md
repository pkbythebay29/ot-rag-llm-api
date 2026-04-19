# Krionis Pipeline 1.1.0

Release date: 2026-04-19

## Summary

This release adds the multi-model runtime update for Krionis Pipeline. Operators and API clients can now choose Hugging Face inference models, choose embedding models independently, rebuild embedding-specific retrieval caches, and carry those runtime selections all the way through query traces and HITL review records.

## Highlights

- Added Hugging Face inference and embedding catalogs in `config/system.yaml`
- Added named runtime profiles for reusable low-resource and higher-quality model combinations
- Added embedding-specific FAISS cache variants so different agents can use different retrieval encoders safely
- Added runtime metadata to approved responses and pending review items
- Added `GET /review/{review_id}/signoff` guidance support for clearer external HITL signoff generation
- Updated the operator UI, configuration UI, website, docs, and notebook walkthrough for the new runtime-selection flow

## Compatibility

- `import rag_llm_api_pipeline` remains supported
- `rag-cli` remains supported
- `krionis-cli` remains supported
- Existing direct `/query` calls still work without runtime overrides

## Validation

- Regression tests passed: `24 passed`
- `ruff check` passed
- `ruff format --check` passed
- `mypy --ignore-missing-imports --no-site-packages rag_llm_api_pipeline` passed
- `mkdocs build --strict` passed
