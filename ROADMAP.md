# Roadmap — Parallax

Three phases, mirroring the BLUEPRINT MVP build path. Each phase mirrors a GitHub milestone; the
public project board tracks the issues under it, so planning and delivery discipline are visible in
the commit history.

## Phase 1 — Drift, observed (mirrors GitHub milestone `phase-1`)

The claimed-versus-observed core, demonstrable on public data.

- Git and issue-tracker connectors (ETL, deterministic metric computation).
- **Claimed Model:** LLM parse of tickets, sprint plans, and status reports into typed state.
- **Observed Model:** deterministic activity metrics (commit/PR flow per epic, review latency, build
  health) plus span-anchored blocker-language claims.
- **Drift Engine:** per-epic Drift Index math, thresholds, and trend windows.
- **PM Morning Brief:** grounded narration over drift findings.
- **Public-history replay demo:** `make replay` reproduces the drift signal on a real open-source
  project's history, so every claim is checkable by a reviewer.
- The eval harness graduates from `NotImplementedError` to enforcing the drift-lead-time thresholds
  in [EVAL.md](EVAL.md).

## Phase 2 — Forecasts, ledgers, and the frontend (mirrors GitHub milestone `phase-2`)

Dates become distributions; promises get a ledger; the UI ships.

- Estimate-history calibration: duration distributions fitted per work type from the team's own
  estimate-versus-actual record.
- Monte Carlo milestone forecasts over the dependency graph, with calendars, capacity, and
  correlated risks; drift findings feed the simulation as live adjustments.
- Meeting ingestion and the **Commitment Ledger** with quote-anchored capture and a one-click
  confirm/reject flow, plus deterministic kept/renegotiated/silently-dropped clocks.
- **Nudge drafts** the PM edits and sends as themselves.
- **Next.js frontend** on the shared portfolio design system: drift views, forecast distributions,
  and the ledger confirmation queue. Demo screenshot and GIF land here.

## Phase 3 — Assumptions, pre-mortems, and full evaluation (mirrors GitHub milestone `phase-3`)

- **Assumption ledger** with owner, validity window, affected milestones, and a compiled
  invalidation tripwire per entry.
- **Pre-mortem engine:** weekly LLM red-team against a curated failure-pattern library; every risk
  must name an observable early signature, which is compiled into a deterministic monitor. No
  signature, no register — speculation is quarantined.
- **Decision-aging radar:** tracks unresolved decisions and escalates ones blocking the critical path.
- **Full replay-evaluation suite:** Brier scores, interval coverage, extraction precision/recall, and
  tripwire lead time against public datasets, published per release.
