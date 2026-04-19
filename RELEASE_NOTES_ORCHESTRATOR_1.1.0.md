# Krionis Orchestrator 1.1.0

Release date: 2026-04-19

## Summary

This release updates Krionis Orchestrator to participate in the shared multi-model runtime flow. Agents can now be started with named runtime profiles or explicit inference and embedding model selections, and that runtime metadata is surfaced back through the orchestration and platform APIs.

## Highlights

- Added runtime-profile aware agent startup in orchestrator-facing routes
- Added per-agent runtime metadata to active agent listings
- Updated orchestrator bridge configuration defaults to align with pipeline runtime profiles
- Kept orchestrator packaging and release automation aligned with the monorepo publish workflow

## Compatibility

- Existing orchestrator APIs remain available
- `krionis-orchestrator` CLI remains supported
- Agents still start without explicit runtime overrides when callers use default YAML assignments

## Validation

- Repository regression suite passed after the feature release updates
- Pipeline and orchestrator package metadata updated together for the 1.1.0 publish
