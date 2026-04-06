# Krionis Platform Docs

Krionis is a human-in-the-loop controlled RAG platform for traceable, reviewable, and extensible knowledge workflows. It is designed so teams can build applications on top of a stable API surface while retaining an immutable audit chain and a mandatory review gate for flagged outputs.

## Platform pillars

- HITL as a control layer: risky or regulated outputs are routed into a review queue instead of being returned directly.
- Traceability by default: every query produces a `trace_id`, and reviewed responses also carry a `review_id`.
- Extensibility: the current RAG flow is wrapped behind an orchestrator hook and tool interface for future agent routing.
- Compliance alignment: system metadata, attributable records, and append-only audit logging are built into the platform.

## Product surfaces

- Interactive API reference: `/api/docs`
- ReDoc reference: `/api/reference`
- OpenAPI schema: `/api/openapi.json`
- Operator query UI: `/`
- Telemetry UI: `/ui/telemetry`
- Runtime UI: `/ui/runtime`
- Configuration UI: `/ui/configuration`
- Result records UI: `/ui/records`
- Reviewer UI: `/ui/reviews`

## Operator workflow

The built-in console is now split into focused pages:

- Operator: start agents, rebuild the retrieval cache, submit controlled queries, route through a selected agent, and rate responses.
- Telemetry: inspect agent inventory, queue telemetry, and recent routed query events.
- Runtime: inspect the main process, worker state, and recent logs.
- Configuration: inspect the active YAML configuration, resolved runtime choices, and local storage paths.
- Records: inspect the locally persisted metadata for quality ratings and review decisions.

## What you can build on top

- Internal copilots for technical operations
- Review dashboards and QA consoles
- Audit export pipelines
- Workflow engines that react to `pending_review` outcomes
- External portals that submit queries and poll trace or review records

## Recommended production topology

The API and docs can evolve independently:

- API service: `api.krionis.com`
- Docs portal: `docs.krionis.com`
- Main marketing/product site: `krionis.com`

This keeps API uptime, docs hosting, and marketing pages decoupled while still presenting a single brand surface.
