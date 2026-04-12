# Krionis Pipeline 1.0.2

Release date: 2026-04-12

## Summary

This release aligns the pipeline package metadata and docs with the renamed repository slug `krionis-platform` and standardizes product naming for production rollout.

## Highlights

- Updated package source URLs to `https://github.com/pkbythebay29/krionis-platform`
- Updated quickstart clone instructions to the renamed repository
- Standardized platform-facing naming in roadmap and runtime comments
- Added a PyPI publishing workflow for controlled package releases from GitHub Actions

## Compatibility

- `import rag_llm_api_pipeline` remains supported
- `rag-cli` remains supported
- `krionis-cli` remains supported

## Validation

- Full test suite passed before release: `22 passed`
