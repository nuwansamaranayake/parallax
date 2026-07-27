# LOOP_STATE — Parallax Phase 1

Branch: `phase-1`. BLUEPRINT L799-907 (App 6): Phase 1 = git plus issue-tracker connectors,
Claimed and Observed models, Drift Index, morning brief. Exit also requires: real eval meeting
EVAL.md bounds (written first), smoke hitting the real keyless business loop, alembic migration
with table count updated, CI eval flipped to required, and the flywheel duty (a Seismograph
contract for the LLM narration stage ships in this repo).

## Milestones (commit each; gate.py after each)

- [x] M1  EVAL.md numeric thresholds first; LOOP_STATE; branch `phase-1`
- [x] M2  engine/gitlog + engine/issues: keyless connectors — structured commit records via
         JSON, deterministic `git log --numstat` parser for local repo paths (verified
         against this repo's own history), issue-tracker JSON import to typed claimed
         items (+tests)
- [x] M3  engine/drift + engine/brief: activity rollups per workstream, deterministic Drift
         Index in [0,1] with the formula documented in code, deterministic morning brief where
         every numeric token traces to a stored stat id (+tests)
- [x] M4  scripts/eval.py: deterministic keyless harness (synthetic histories with planted
         drift + healthy control + edge cases) meeting the pre-written EVAL.md bounds; all
         four bounds observed PASS at 1.0; byte-reproducible report
- [x] M5  schema + alembic 0002 (projects, workstreams, claimed_items, observed_commits,
         activity_rollups, drift_indices, briefs, brief_stats) EXPECTED_TABLE_COUNT=9
         (MIGRATION OK: 9 tables observed); API (projects, claimed/observed imports, drift
         compute+read, brief compute+read, key-gated narrate); CLI `python -m app.cli brief`
         (exit 1 on flagged drift observed); smoke = real keyless loop (SMOKE OK observed);
         Dockerfile migrate-on-start
- [x] M6  flywheel: contracts/brief-narration.yaml validating against Seismograph's DSL
         (plan_id 318d41625ecbccd8 via its loader, cwd Seismograph); key-gated narration
         through the gateway; eval_llm observed: coverage 1.00, accepted 1.00, repeat
         jaccard 0.90, paraphrase jaccard 0.67
- [x] M7  CI eval -> "eval (required)"; README/contracts.md/CHANGELOG truth pass;
         FAILURES.md FAIL-0004 (stat rendering round-trip) with regression pin

## DECISION log
- Zero-key product path: both connectors are JSON/data-entry (commit records, issue records)
  and the drift + brief pipeline is fully deterministic, so the whole core loop runs keyless.
  The LLM stage is narration polish only, key-gated with a typed 503 (Standard 3: the
  deterministic brief is the product, never a fallback label).
- Epic naming: the blueprint says epics; Phase 1 models them as `workstreams` (a workstream
  can be an epic, a component, or a team stream). contracts.md rows updated to match.
- Drift formula (documented in engine/drift.py): drift = max(0, claimed_fraction −
  observed_fraction) for workstreams with incomplete claimed work; completed workstreams are
  excluded (done work needs no activity). Bounded [0,1] by construction.
- Stat identity: stat ids are deterministic app-assigned tokens (`ws:<key>:<metric>`), never
  model-invented names (CareerCompiler FAIL-0003: canonicalize before comparing). The
  narration gate accepts only sentences citing existing stat ids.

## BLOCKED
(none)

## Next task
NONE — Phase 1 GATES_PASSED (2026-07-27). All DONE-WHEN items observed: gate.py exit 0
(ruff, 24 pytest, live keyless business-loop smoke, eval all bounds 1.0), MIGRATION OK: 9
tables against the throwaway Postgres, prod-guard (APP_ENV=production: /api/v1/demo 503 and
GET /api/v1/projects/1/drift 200 with 3 rows), eval report byte-reproducible (two runs,
cmp identical), flywheel contract validated via Seismograph's loader (plan_id
318d41625ecbccd8) + key-gated LLM eval observed (coverage 1.00, accepted 1.00, repeat
jaccard 0.90, paraphrase jaccard 0.67 on google/gemini-2.5-flash). Branch `phase-1`,
NOT pushed.
