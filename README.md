# Parallax

> **Status: Phase 1 core loop released (v0.3.1).** Git-log and issue-tracker
> connectors (keyless JSON, plus a local-repo git parser), the Claimed and Observed models,
> a deterministic per-workstream Drift Index, and a morning brief in which every number
> traces to a stored stat id. The LLM narration stage is key-gated polish on top. The eval
> suite enforces bounds that were committed before the harness existed.
> [ROADMAP.md](ROADMAP.md) shows what exists today versus what is next.

**An AI assistant for project managers: claimed-versus-observed project instrumentation.**

Every project has two realities: the one in the status reports and the one in the commits,
calendars, and chat threads. Parallax continuously measures the gap between them, quantifies what
the gap does to your dates, and tracks the promises and assumptions that never made it into a ticket.

## What it is

The PM-AI category automates the clerical layer: summarize the meeting, draft the status update,
generate subtasks (the tools we reviewed as of July 2026). Useful, and beside the point. Projects do not fail because summaries were slow.
They fail because the board said "on track" for five weeks while the commit graph flatlined, because
a promise made in a Wednesday sync was never written down and silently died, and because the risk
that killed the timeline was one everybody privately suspected and nobody was assigned to watch.
Parallax is the instrument that audits the system of record instead of building on it.

## How it works (the design)

Two models run continuously, and a deterministic engine diffs them:

- **Claimed Model** parses tickets, sprint plans, and status reports into typed state.
- **Observed Model** derives from activity exhaust: commit and PR flow per epic, review latency,
  build health, calendar load of assigned people, and blocker language in consented channels.
- **Drift Engine** computes a per-epic **Drift Index**: claimed progress versus observed
  trajectory, claimed staffing versus observed attention, claimed "no blockers" versus
  blocker-language frequency. Sustained drift, not any single signal, raises the flag.

On top of Phase 1 drift, later phases add a Monte Carlo forecaster that turns dates into
distributions calibrated on the team's own estimate-versus-actual history, quote-anchored
Commitment and Assumption ledgers with silent-drop detection, and a weekly pre-mortem whose risks
are compiled into deterministic tripwires. Every outbound nudge is drafted for the PM to edit and
send as themselves. Parallax drafts, never sends.

## What exists today (verified)

The doctrine is enforced, not promised. Checks you can run yourself, each observed passing:

1. `python scripts/eval.py`: the planted-drift suite against bounds written before the
   harness. Observed: drift detection 1.0 (the workstream claiming 80 percent done with
   near-zero activity ranks highest in every case), control quiet 1.0, brief groundedness
   1.0 (every numeric token matches a stored stat), index bounds 1.0. Two consecutive runs
   produce byte-identical reports.
2. `python scripts/smoke_test.py` against a running instance: creates a project, imports
   claimed items and commit records, computes drift, builds the brief, reads both back.
   The whole loop is keyless. Observed: `SMOKE OK`.
3. `alembic upgrade head && python scripts/check_migrations.py`: observed
   `MIGRATION OK: 9 tables` against a real Postgres (8 app tables plus alembic_version).
4. Set `APP_ENV=production` and call `/api/v1/demo`: returns 503, because fixture data
   outside development is forbidden by code, not by convention.
5. `python -m app.cli brief --data data/synthetic/golden/golden.json --case planted-drift`:
   prints the grounded brief and exits 1 because drift is flagged, so scripts can branch
   on it. Observed.
6. Key-gated narration measured for real (`scripts/eval_llm.py`, google/gemini-2.5-flash):
   citation coverage 1.00, accepted fraction 1.00, repeat-run jaccard 0.90, paraphrase
   jaccard 0.67, against `contracts/brief-narration.yaml` (validated with Seismograph's
   own contract loader). Without a key the narrate endpoint refuses with a typed 503.

## The unique bet

No open PM tool we reviewed (July 2026) makes its core objects the measured gap between claimed and observed state, a calibrated probabilistic date forecast, and ledgers for promises and assumptions that never became tickets. That is the bet.

The full scoped novelty statement, with the field surveyed, is in [PRD.md](PRD.md).

Incumbents are structurally loyal to the claimed reality because
tickets are their data moat; a tool whose thesis is "your tickets are lying" has to live outside the
ticket vendor, and open source is the only version a measured team should accept.

## Quickstart (local, zero external keys)

### Standalone clone

```bash
python -m venv .venv
source .venv/bin/activate         # POSIX     (.venv\Scripts\activate on Windows)
pip install -e .[dev]             # groundwork resolves from GitHub automatically
cp .env.example .env              # POSIX     (copy .env.example .env on Windows)
uvicorn app.main:app --reload
```

### Developing the whole portfolio (sibling checkout, editable)

```bash
git clone https://github.com/nuwansamaranayake/groundwork ../groundwork
pip install -e ../groundwork
pip install -e .[dev]
```

Then, with Postgres up (`docker compose up -d db`) and the schema applied
(`alembic upgrade head && python scripts/check_migrations.py`), in another shell:

```bash
export API_PORT=8000 SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py   # POSIX -> SMOKE OK
set API_PORT=8000 && set SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py  # Windows
```

The smoke test runs the full keyless business loop: project, imports, drift, brief. No
OpenRouter key is needed anywhere in the core product; the key unlocks only the narration
polish endpoint. The CLI needs even less: `python -m app.cli brief` runs the whole loop in
memory with no server and no database.

## Demo

A screenshot and a `make replay` GIF of the Drift Index leading a real public-history slip land in
Phase 2 with the Next.js frontend. Until then, the synthetic `/api/v1/demo` payload shows the shape
of a per-epic drift snapshot.

## Doctrine

The operating rules for this repo, fail loud, smoke-test real endpoints, no silent fallbacks, live
in [DOCTRINE.md](DOCTRINE.md). The sensor-not-judge split specific to Parallax is recorded in
[docs/adr/0002-llm-senses-deterministic-decides.md](docs/adr/0002-llm-senses-deterministic-decides.md).
