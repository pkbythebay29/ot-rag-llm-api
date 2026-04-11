# Compliance Assessment

Krionis can assess regulated documents against a regulation corpus that you manage as an indexed system. This keeps compliance review inside the same controlled-query, HITL, and audit framework as the rest of the platform.

## What the feature does

- Accept a regulated document as inline text or a local file path
- Build a structured compliance assessment question
- Retrieve against the selected regulation system
- Generate an assessment through the normal Krionis pipeline
- Route flagged results into the review queue
- Persist the assessment in local SQLite for later inspection

## API

Primary endpoints:

- `POST /compliance/assess`
- `GET /compliance/assessments`
- `GET /compliance/assessments/{assessment_id}`
- `GET /compliance/pools`
- `POST /compliance/pools`
- `POST /compliance/pools/{pool_name}/rebuild`
- `POST /compliance/pools/{pool_name}/start-agent`

The response includes the usual Krionis control metadata:

- `status`
- `trace_id`
- `review_id` when HITL is required
- `assessment_id`
- `regulation_system`

## Input model

You can submit either:

- `document_text`
- `document_path`

Relative document paths resolve from `settings.data_dir`.

Optional fields:

- `regulation_system`
- `framework`
- `focus`

## Regulation-only data pools

Krionis now supports dedicated regulation-only corpora, so teams do not need to mix SOPs, manuals, and regulations into one index.

Use a pool to:

- point Krionis at a folder that contains only regulatory documents
- rebuild that pool independently
- start the built-in `regulatory` agent against that pool
- select the pool as the `regulation_system` for compliance assessments

This makes the regulatory wire easier to operate from both the UI and external API clients.

## Storage and traceability

Compliance assessments are stored separately from review items and quality feedback:

- compliance SQLite store: `compliance.sqlite_path`
- review SQLite store: `review_store.sqlite_path`
- append-only audit log: `audit.log_path`

This means you can trace:

- the submitted regulated document excerpt
- the assessment question
- the generated response
- the HITL review decision
- the final approved assessment text

## UI

The built-in compliance operator page is available at:

- `/ui/compliance`

It lets operators:

- create and manage regulation-only pools
- rebuild a regulation pool index
- start the built-in regulatory agent
- submit a document for assessment
- view recent assessment status
- open the review dashboard for signoff when needed

## Notebook-first exploration

The repo also includes a ready-to-run Jupyter notebook for operators, solution engineers, and platform integrators:

- `notebooks/krionis_regulatory_wire_walkthrough.ipynb`

It demonstrates the full regulatory wire from pool creation through review approval, which makes it a useful onboarding path for GitHub-first users.
