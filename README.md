# Parallax

> **Status: scaffold (v0.1).** The engineering harness is built and verified: live smoke test,
> fail-loud guards, migration checks, CI. The architecture described below is the design being
> built; Phase 1 is in progress. [ROADMAP.md](ROADMAP.md) shows what exists today versus what
> is next.

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

This scaffold's doctrine is already enforced, not promised. Three checks you can run in five minutes:

1. `python scripts/smoke_test.py` against a running instance: hits real endpoints and asserts
   non-empty, schema-valid data. Passes.
2. Set `APP_ENV=production` and call `/api/v1/demo`: returns 503, because fixture data outside
   development is forbidden by code, not by convention.
3. `python scripts/eval.py`: raises loudly instead of passing vacuously. An eval that cannot
   fail is theater; the real harness lands in Phase 1.

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

Then, in another shell:

```bash
export API_PORT=8000 SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py   # POSIX -> SMOKE OK
set API_PORT=8000 && set SMOKE_TEST_TOKEN=dev && python scripts/smoke_test.py  # Windows
```

The `/api/v1/demo` endpoint serves the synthetic dataset in `data/synthetic/`: no OpenRouter key, Postgres, or Redis is needed to see the app respond. Those are required only for Phase 1 features (real extraction, persistence, migrations).

## Demo

A screenshot and a `make replay` GIF of the Drift Index leading a real public-history slip land in
Phase 2 with the Next.js frontend. Until then, the synthetic `/api/v1/demo` payload shows the shape
of a per-epic drift snapshot.

## Doctrine

The operating rules for this repo, fail loud, smoke-test real endpoints, no silent fallbacks, live
in [DOCTRINE.md](DOCTRINE.md). The sensor-not-judge split specific to Parallax is recorded in
[docs/adr/0002-llm-senses-deterministic-decides.md](docs/adr/0002-llm-senses-deterministic-decides.md).
