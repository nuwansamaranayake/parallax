# Changelog

All notable changes to Parallax are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- Business read endpoints (GET /api/v1/projects/{id}/drift, /workstreams/{id}/drift, /brief) now require the same bearer token as writes. They
  previously served real production data to unauthenticated callers (FAILURES FAIL-0007).

## [0.2.0] - 2026-07-23

### Added — Phase 1 drift core
- Keyless connectors: issue-tracker JSON import (typed claimed items) and commit-record
  JSON import, plus a deterministic `git log --numstat` parser for local repo paths
  (`python -m app.cli ingest-git`), with path-prefix workstream attribution resolved and
  stored at import; unattributed commits stay visible, never dropped.
- Deterministic Drift Index per workstream (formula documented in `app/engine/drift.py`,
  bounded [0,1] by construction; completed and unclaimed workstreams excluded explicitly).
- Morning brief assembled only from computed statistics: every numeric token carries its
  stat id in brackets, the full stat trace is part of the document, and `brief_stats`
  stores the exact rendered token so formatting round-trips through the database.
- Persisted API loop (projects, imports, drift compute/read, brief build/read, workstream
  detail) with bearer auth; alembic 0002 applies `app.db.metadata`
  (MIGRATION OK: 9 tables observed); container migrates and asserts count before serving.
- Key-gated narration endpoint through the groundwork gateway: strict JSON schema, every
  accepted sentence must cite existing stat ids, rejects returned with reasons, typed 503
  without a key. Observed real-run metrics (google/gemini-2.5-flash): citation coverage
  1.00, accepted fraction 1.00, repeat-run jaccard 0.90, paraphrase jaccard 0.67.
- Eval harness enforcing bounds committed before the harness existed: drift detection 1.0,
  control quiet 1.0, brief groundedness 1.0, index bounds 1.0, byte-reproducible report
  (`eval_report.md`); key-gated narration report in `eval_report_llm.md`.
- Flywheel: `contracts/brief-narration.yaml` validated against Seismograph's contract DSL
  (plan_id 318d41625ecbccd8 via its own loader).
- CLI `python -m app.cli brief` runs the loop in memory and exits nonzero when drift is
  flagged, so scripts can branch on it.

### Changed
- CI eval job is now REQUIRED ("eval (required)") with lean keyless deps.
- Smoke test exercises the full keyless business loop (project, imports, drift, brief),
  not just health + fixture.

### Changed
- Dependency on `aignite-groundwork` switched from an editable path source to a pinned git
  dependency (`git+https://github.com/nuwansamaranayake/groundwork@v0.1.0`) so standalone clones and CI resolve
  it without a sibling checkout. PyPI publication planned at first release.
- `scripts/check_migrations.py` now uses `DATABASE_URL` with the declared psycopg v3 driver
  unmodified, fixing a clean-machine `make migrate` failure (see FAILURES.md FAIL-0002).
- README truth pass: scaffold status block, `(the design)` heading, "What exists today (verified)"
  section, scoped/dated novelty, dual-path Quickstart, em-dash sweep.
- CI: Python matrix (3.12, 3.13); eval job labeled "eval (Phase 1 pending)".

### Added
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) and a SECURITY.md vulnerability-reporting policy.

### Fixed — adversarial review wave (10 confirmed findings, see FAILURES.md FAIL-0005)
- Groundedness scanner counts only free-standing numbers: digits inside workstream or
  project names ("v2-api", "ui5") no longer register as ungrounded tokens that reject true
  narration sentences; new `digit-names` golden eval case pins it.
- Imports are idempotent: unique indexes on `claimed_items (workstream_id, item_key)` and
  `observed_commits (project_id, sha)` (alembic 0003, with dedupe for pre-existing rows)
  and `ON CONFLICT DO UPDATE` upserts, so re-delivered tracker exports and commit payloads
  converge instead of double-counting claims and churn.
- Drift state is single-row-per-workstream under concurrency: unique indexes on
  `drift_indices.workstream_id` and `activity_rollups.workstream_id` plus upserts in
  `drift/compute`.
- LLM narration call moved outside the DB transaction (read session, gateway call with no
  connection held, then a write transaction) and bounded by `LLM_TIMEOUT_SECONDS`
  (default 60s; previously the OpenAI-client default of 600s could pin pooled
  connections).
- `compute_drift` fails loudly on commits or items naming undeclared workstreams
  (matching the API's 422 at import) instead of silently skewing `max_*` or dropping
  items on the CLI/eval path.
- `scripts/check_migrations.py` refuses to run as a silent no-op: an unset
  `EXPECTED_TABLE_COUNT` now fails with a typed message instead of printing MIGRATION OK
  for a check that never happened.
- Narration with a missing model slot returns the typed 503 naming
  `LLM_MODEL_EXTRACTION` (the error previously escaped as a 500 blaming
  `LLM_MODEL_REASONING`).
- `.dockerignore` added: `COPY . .` no longer bakes `.env` (live keys) or `.git` into
  images built by the documented compose flow.
- CI test job installs groundwork from the same pin as pyproject
  (`nuwansamaranayake/groundwork@v0.1.0`, was the wrong owner) and the error-masking
  `||` fallbacks are gone.
- contracts.md claim is now backed by CI: the smoke job runs
  `scripts/check_contracts.py`, asserting every `implemented` row exists in the live
  `/openapi.json` spec.

## [0.1.0] - 2026-07-21
### Added
- Engineering harness scaffold: governed doc set, config guard, verification gates,
  smoke test against a real business endpoint, migration-count check, CI pipeline,
  and a synthetic dataset so the demo runs with zero external keys.
