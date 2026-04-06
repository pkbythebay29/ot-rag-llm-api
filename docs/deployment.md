# Deployment

## Docs portal recommendation

For a production-grade docs portal, this repository is set up to work well with a static docs host using MkDocs and Material for MkDocs.

Recommended deployment split:

- `api.krionis.com` for the FastAPI service
- `docs.krionis.com` for the static docs portal
- optional redirect from `krionis.com/docs` to `docs.krionis.com`

## Build the docs site

Install the docs dependencies:

```bash
pip install -r requirements-docs.txt
```

Build locally:

```bash
mkdocs build --strict
```

Serve locally:

```bash
mkdocs serve
```

## Container deployment

An integrated container path is included for the API plus orchestrator runtime.

Build and start:

```bash
docker compose up --build
```

The compose file persists:

- `./config`
- `./data`
- `./indices`

This keeps:

- source manuals
- retrieval indexes
- review queue records
- audit logs
- result metadata

outside the image for easier backup and validation.

## Runtime storage

The platform now persists operational records locally:

- review queue: SQLite
- result metadata for ratings and review outcomes: SQLite
- audit trail: append-only JSONL

That split keeps the mutable workflow state queryable while preserving the append-only audit log separately.

## Production considerations

- Keep the docs site static and separately deployable from the API.
- Treat OpenAPI and Markdown docs as versioned release assets.
- Publish docs builds through CI on every pull request and main branch merge.
- Keep the OpenAPI URLs stable so external integrators can automate against them.

## Domain strategy

Using a dedicated docs subdomain keeps the experience cleaner for integrators and easier to host behind enterprise CDN and DNS controls. If branding requires `krionis.com/docs`, route that path to the docs host or redirect it to `docs.krionis.com`.
