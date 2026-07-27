# Failure Gallery — Parallax

An honest record of things that broke, why, and what changed. A curated gallery beats a buried
changelog: it is where the doctrine earns its keep. Every entry names the *reported* symptom and
the *diagnosed* root cause separately (Standard 5).

> The entry below is a seeded template. Replace it with the first real failure you diagnose.

## FAIL-0001 (template) — Demo showed no data

- **Date**: 2026-07-21
- **Surface**: `GET /api/v1/demo`
- **Reported symptom**: The demo view rendered "no data".
- **Diagnosed cause**: `data/synthetic/demo.json` existed but was an empty array. The endpoint
  correctly raised HTTP 500 (`"synthetic fixture is empty"`) instead of silently returning `[]`.
- **Root cause**: Fixture authored empty during scaffold.
- **Fix**: Populated the fixture with a non-empty synthetic dataset. The smoke test asserts
  `items` is non-empty, so this cannot regress silently.
- **Doctrine link**: Standard 3 (no silent mock/fallback) and Standard 2 (smoke asserts non-empty).

## FAIL-0002 — `make migrate` failed on a clean machine (check_migrations driver)

- **Date**: 2026-07-21
- **Surface**: `scripts/check_migrations.py` (`make migrate`)
- **Reported symptom**: The migration-count check errored immediately after a successful
  `alembic upgrade`.
- **Diagnosed cause**: The script did `DATABASE_URL.replace("+psycopg", "")`, turning
  `postgresql+psycopg://...` into a bare `postgresql://...`. SQLAlchemy routes the bare URL to the
  **psycopg2** driver, which is not a declared dependency (the apps pin `psycopg` v3). `alembic`
  itself succeeded because it kept the `+psycopg` URL, so the failure surfaced only at the check step.
- **Root cause**: Driver mismatch between the migration step (psycopg v3) and the check step (psycopg2).
- **Fix**: Use `DATABASE_URL` unmodified so the check reuses the declared psycopg v3 driver. Proven
  against a real Postgres: `MIGRATION OK: 1 tables` at `EXPECTED_TABLE_COUNT=1`, and
  `MIGRATION CHECK FAILED: expected 2 tables, found 1` (rc=1) at `EXPECTED_TABLE_COUNT=2`.
- **Doctrine link**: Standard 4 (assert the table count) and Standard 1 (fix the root cause — the
  driver — not the symptom).

## FAIL-0003 — First public CI run: smoke job died before the stack started

- **Date**: 2026-07-23
- **Surface**: GitHub Actions `smoke` job (`docker compose up -d --build`)
- **Reported symptom**: CI run red on the first push; compose exited immediately.
- **Diagnosed cause (from the run log)**: `env file ... .env not found`. `docker-compose.yml`
  declares `env_file: .env`, and `.env` is gitignored by design, so it does not exist in a CI
  checkout. A second, deterministic failure sat behind it: the Dockerfile's `pip install .` now
  resolves `aignite-groundwork` from a `git+https` URL, and `python:3.12-slim` ships no git.
- **Root cause**: The CI environment was never given the dev-shaped inputs the compose file
  assumes (env file present, git available in the build image).
- **Fix**: CI smoke job copies the committed `.env.example` to `.env` before compose (the same
  step the README gives a stranger); Dockerfile installs git before `pip install`.
- **Doctrine link**: Standard 1 (root cause from the real log, not a retry) and Standard 2 (the
  smoke gate exists to catch exactly this before anyone calls the estate "green").

## FAIL-0004 — Integer stats lost their identity through the database, so narration would
## have rejected true sentences

- **Date**: 2026-07-27
- **Surface**: `POST /api/v1/briefs/{id}/narrate` (stat reload in `app/routes.py`), caught
  during implementation review before the first commit of the route.
- **Reported symptom** (would have been): the narration gate rejecting perfectly grounded
  sentences like "Search logged 12 commits." as carrying "ungrounded numbers" — but only
  for briefs reloaded from the database, never for briefs still in memory, an
  intermittent-looking failure that is actually deterministic.
- **Diagnosed cause**: `brief_stats.value` is a Float column. Reloading turns the int stat
  `12` into `12.0`, and the canonical formatter then renders `"12.00"` while the brief and
  the model both say `"12"`. Observed repro: `fmt(float(12)) == '12.00'`. String-exact
  groundedness comparison is the product's spine, so a formatting drift is a correctness
  bug, not cosmetics.
- **Root cause**: the schema stored the numeric value but not the numeric *rendering*, and
  the groundedness contract is defined over renderings.
- **Fix**: `brief_stats.rendered` stores the exact token that appears in the brief
  (`fmt(value)` at write time); reload reconstructs the typed value from `rendered`. The
  stub-gateway API test now echoes an integer stat verbatim and fails if the round-trip
  ever drifts again.
- **Doctrine link**: the portfolio thesis (canonicalize before you compare — same lesson as
  CareerCompiler FAIL-0003, this time for numbers instead of names) and Standard 4's spirit:
  what the database returns must be asserted, not assumed.

## FAIL-0005 — Adversarial review wave caught ten confirmed defects before release

- **Date**: 2026-07-27
- **Surface**: whole repo — engine, routes, schema, scripts, CI, Dockerfile, contracts.md.
  Caught by an adversarial code review (every finding verified by live repro against this
  code) before any release shipped.
- **Findings**: 10 confirmed (4 major, 6 minor). The worst:
  - The groundedness scanner's bare `\d+` counted digits inside workstream/project names
    as numeric tokens — a workstream named "v2-api" produced false ungrounded tokens that
    rejected every true narration sentence naming it, and would have false-failed the
    eval's groundedness bound. The golden fixtures happened to be digit-free, so nothing
    covered it (major).
  - No `.dockerignore` existed, so `COPY . .` baked the gitignored `.env` — holding a
    real OPENROUTER_API_KEY — plus `.git` into every image built by the documented
    compose flow (major).
  - The narration route ran the LLM network call inside an open DB transaction with no
    client timeout configured (OpenAI default 600s): ~15 slow narrations would exhaust
    the connection pool for every endpoint (major).
  - Imports were append-only with no unique constraints: re-importing a tracker export
    after todo->done double-counted claims at half weight, and a re-posted commit payload
    silently doubled commit counts and churn through every downstream number (major).
- **Fixes**: boundary-guarded numeric scan + `digit-names` eval case; `.dockerignore`;
  read-txn -> LLM call -> write-txn split with `LLM_TIMEOUT_SECONDS` bound; unique
  indexes + upserts (alembic 0003) for idempotent imports and single-row drift state;
  loud failures for undeclared workstreams, unset `EXPECTED_TABLE_COUNT`, and the unset
  narration model slot; CI groundwork pin corrected and fallbacks removed; contracts.md
  claim backed by a real CI check (`scripts/check_contracts.py`).
- **Doctrine link**: Standard 3 (fail loud, never silently skip or skew), Standard 4
  (assert what the database holds), Standard 6 (contracts.md must match the live spec),
  and the GoviHub lesson — every silent-failure path found here is the class this repo
  exists to instrument against. An adversarial review of the "finished" tree found what
  the green gate could not; the gate now tests for each of these regressions.

## FAIL-0006 — Eval report embedded an environment-dependent line, breaking byte-reproducibility across environments

- **Date**: 2026-07-23
- **Surface**: `scripts/eval.py` report writer (central post-fix verification sweep)
- **Reported symptom**: the committed eval_report.md differed by one trailer line when the
  gate ran in a shell with a different OPENROUTER_API_KEY state.
- **Diagnosed cause**: the key-gated-section status note (present/absent by ambient env) was
  written into the report file, so "byte-reproducible" only held within one environment.
- **Fix**: the note now goes to stdout only; the report file is purely deterministic. Verified
  by running the eval with and without a key and comparing byte-for-byte.
- **Doctrine link**: reproducibility bounds must be environment-independent, or they are
  theater in every environment except the author's.

## FAIL-0007 — Production business data was world-readable: read endpoints skipped bearer auth

- **Date**: 2026-07-27
- **Surface**: `GET /api/v1/projects/{id}/drift, /workstreams/{id}/drift, /brief`
- **Reported symptom**: none. Every gate was green, CI was green, and the estate smoke
  passed: the smoke client always sent a token, so it never asked what happens without one.
- **Diagnosed cause**: mutating endpoints called `_auth(authorization)`; these read
  endpoints never took an `authorization` header at all. Verified against live production
  from an unauthenticated client on the public internet, which returned HTTP 200 and
  claimed-versus-observed project status and morning briefs.
- **Root cause**: the adversarial review found this class and fixed the two instances it
  happened to surface (CareerCompiler `get_fit`, Mycelium `get_answer`); the class was
  never swept estate-wide, so four apps shipped with open reads.
- **Fix**: every business read now calls the same `_auth` as the writes. Development
  semantics are unchanged (an empty `SMOKE_TEST_TOKEN` leaves auth off, and production
  startup already refuses an empty token). Regression test added:
  `test_business_reads_require_bearer_when_token_set` asserts 401 without a bearer.
- **Doctrine link**: Standard 6 — this is exactly why the estate needed `API_CONTRACT.md`
  with an auth column: an endpoint nobody wrote down is an endpoint nobody audited. The
  production business-loop audit (curl with and WITHOUT a token) caught what six green
  CI runs could not.

## FAIL-0008 — Every published hostname 404ed at the root URL

- **Date**: 2026-07-27
- **Surface**: `GET /` on `https://parallax.aigniteconsulting.ai`
- **Reported symptom**: none from any gate. A browser visiting the hostname received
  `404 {"detail":"Not Found"}` as `application/json`, measured in production.
- **Root cause, named correctly**: The front door 404ed on every published hostname because the estate gate asserted /health and the business loop and never asserted what a browser receives at the root URL, and a gate that tests only the paths its author remembers will pass forever while the front door is broken.
- **Not the cause**: a missing decorator on six apps. That is the instance. The class is an
  unswept assertion gap, the same shape as the 2026-07-27 unauthenticated-reads incident,
  where a defect found in two repos was fixed in those two and never swept across the estate.
- **Fix**: `GET /` serves a self-contained static page on every app, and the gap is closed as
  a class in two places. Each `scripts/gate.py` asserts the root route returns 200 `text/html`
  carrying the app name and the EVAL.md limits sentence verbatim. `estate_smoke.py` sends a
  browser-shaped request (`Accept: text/html`) to every hostname it finds **by parsing
  API_CONTRACT.md**, not from a literal list, so a seventh app is covered without editing the
  gate, and it fails on placeholder text.
- **Doctrine link**: rule 9, sweep the class not the instance. Also rule 10: the hostname
  enumeration fails loudly when it finds no hostnames, rather than passing over an empty set.

## Incident record

The 2026-07-27 unauthenticated-reads incident, which affected this repo, is documented in the
estate's operational repo:
[portfolio-ops/docs/postmortem/2026-07-27-unauthenticated-reads.md](https://github.com/nuwansamaranayake/portfolio-ops/blob/main/docs/postmortem/2026-07-27-unauthenticated-reads.md)

It covers the exposure window, the access-log finding (there were none), the data
classification (synthetic only, proven by query), the root cause, and the controls now in
place, including the `route_auth()` class check in `scripts/gate.py`.
