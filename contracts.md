# API contracts — Parallax

Per Standard 6, every frontend call (the Next.js UI arrives in Phase 2) maps to exactly one backend
endpoint, and CI diffs this file against the live OpenAPI spec at `/openapi.json` (Swagger UI at
`/docs`). Implemented endpoints are live today; everything else is planned and marked as such — no
frontend call may reference an endpoint that does not exist in the spec.

| Frontend call (Phase 2) | Method | Path | Status | Notes |
|---|---|---|---|---|
| Liveness / env probe | GET | `/health` | implemented | Returns `{status, env}`. No auth. |
| Demo drift snapshots | GET | `/api/v1/demo` | implemented | Serves the synthetic `data/synthetic/` dataset. Development-only; returns 503 outside `development`. |
| List project drift snapshots | GET | `/api/v1/projects/{project_id}/drift` | planned — Phase 1 | Per-epic Drift Index, claimed-vs-observed fields, and trend window for a project. |
| Epic drift detail | GET | `/api/v1/epics/{epic_id}/drift` | planned — Phase 1 | Full claimed/observed breakdown and the evidence spans behind the flag for one epic. |
| PM morning brief | GET | `/api/v1/projects/{project_id}/brief` | planned — Phase 1 | Grounded narration over drift findings for the current day. |
| Milestone forecast | GET | `/api/v1/milestones/{milestone_id}/forecast` | planned — Phase 2 | Monte Carlo distribution: on-time probability, P80 date, top variance contributors. |
| Commitment ledger | GET | `/api/v1/projects/{project_id}/commitments` | planned — Phase 2 | Quote-anchored commitments with kept/renegotiated/dropped status. |
| Confirm or reject a ledger entry | POST | `/api/v1/commitments/{commitment_id}/confirm` | planned — Phase 2 | One-click human confirmation; unconfirmed entries do not count. Idempotency key required. |
| Tripwire monitors | GET | `/api/v1/projects/{project_id}/tripwires` | planned — Phase 3 | Compiled deterministic monitors from assumptions and pre-mortem risks, with fire state. |
