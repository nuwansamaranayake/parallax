# API contracts — Parallax

Per Standard 6, every frontend call (the Next.js UI arrives in Phase 2) maps to exactly one backend
endpoint. CI's smoke job runs `scripts/check_contracts.py` against the live stack: every row below
marked `implemented` must exist in the live OpenAPI spec at `/openapi.json` (Swagger UI at `/docs`),
and the build fails on drift. Implemented endpoints are live today; everything else is planned and
marked as such — no frontend call may reference an endpoint that does not exist in the spec.

| Frontend call (Phase 2) | Method | Path | Status | Notes |
|---|---|---|---|---|
| Front page (browser) | GET | `/` | none | Self-contained HTML: thesis, what it measures, the EVAL.md limits sentence, the endpoint list, build stamp. Public by design. |
| Liveness / env probe | GET | `/health` | implemented | Returns `{status, env}`. No auth. |
| Demo drift snapshots | GET | `/api/v1/demo` | implemented | Serves the synthetic `data/synthetic/` dataset. Development-only; returns 503 outside `development`. |
| Create project + workstreams | POST | `/api/v1/projects` | implemented | Workstream keys unique; path prefixes drive commit attribution. Bearer auth when `SMOKE_TEST_TOKEN` set. |
| Import claimed items | POST | `/api/v1/projects/{project_id}/claimed/import` | implemented | Issue-tracker JSON connector (keyless). 422 on unknown workstream keys or malformed rows. |
| Import observed commits | POST | `/api/v1/projects/{project_id}/observed/import` | implemented | Commit-record JSON connector (keyless); attribution resolved and stored at import. Local-repo path via `python -m app.cli ingest-git`. |
| Compute drift | POST | `/api/v1/projects/{project_id}/drift/compute` | implemented | Deterministic rollups + Drift Index per workstream (formula in `app/engine/drift.py`, in [0,1]). Replaces the project's previous rows (current-state semantics; history in Phase 2). |
| List project drift | GET | `/api/v1/projects/{project_id}/drift` | implemented | Stored per-workstream Drift Index rows, sorted by drift descending. Phase 1 models epics as workstreams. |
| Workstream drift detail | GET | `/api/v1/workstreams/{workstream_id}/drift` | implemented | One workstream's stored drift row plus its activity rollup. |
| Build morning brief | POST | `/api/v1/projects/{project_id}/brief` | implemented | Deterministic markdown; every number carries a stat id and is persisted in `brief_stats`. |
| PM morning brief | GET | `/api/v1/projects/{project_id}/brief` | implemented | Latest stored brief with its full stat trace. |
| Narrate brief (LLM polish) | POST | `/api/v1/briefs/{brief_id}/narrate` | implemented | Key-gated: typed 503 without `OPENROUTER_API_KEY`. Every accepted sentence cites existing stat ids; rejects are returned, never dropped. |
| Milestone forecast | GET | `/api/v1/milestones/{milestone_id}/forecast` | planned — Phase 2 | Monte Carlo distribution: on-time probability, P80 date, top variance contributors. |
| Commitment ledger | GET | `/api/v1/projects/{project_id}/commitments` | planned — Phase 2 | Quote-anchored commitments with kept/renegotiated/dropped status. |
| Confirm or reject a ledger entry | POST | `/api/v1/commitments/{commitment_id}/confirm` | planned — Phase 2 | One-click human confirmation; unconfirmed entries do not count. Idempotency key required. |
| Tripwire monitors | GET | `/api/v1/projects/{project_id}/tripwires` | planned — Phase 3 | Compiled deterministic monitors from assumptions and pre-mortem risks, with fire state. |
