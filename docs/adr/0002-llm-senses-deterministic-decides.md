# 2. The LLM senses; deterministic code decides

Date: 2026-07-21

## Status

Accepted

## Context

Parallax measures the gap between what a project claims and what its activity shows, forecasts
milestone dates, and tracks fragile promises and assumptions. Every one of those outputs is
consequential: a drift flag reshapes staffing, a forecast reshapes commitments to stakeholders, a
dropped-commitment alert names a person. The portfolio thesis is that a language model is a
**sensor**, not a judge — it turns messy reality (tickets, commit messages, meeting transcripts,
channel chatter) into typed, provenance-carrying claims, and deterministic code verifies those
claims, makes every decision, and computes every number. Parallax is the capstone, so it has to
embody that split precisely, not gesture at it. The alternative — letting the model estimate a
completion probability or decide that an epic is "at risk" — would produce confident, unfalsifiable,
un-reproducible numbers, which is exactly the status theater the product exists to replace.

## Decision

We draw a hard line, matching the chapter's Deterministic-vs-Non-Deterministic table.

**What the LLM senses (non-deterministic, always quote/span-anchored):**
- Parsing tickets, sprint plans, and status reports into the Claimed Model's typed state.
- Blocker-language claims from channels, anchored to the source span.
- Commitment and assumption extraction from transcripts — quote-anchored and human-confirmed before
  it counts.
- Pre-mortem risk generation, which must name an observable signature or be quarantined.
- Work-type classification, and grounded narration of the morning brief.

**What deterministic code decides and computes:**
- Connector ETL and all observed-metric computation.
- The Drift Index math, thresholds, and trend windows.
- Duration-distribution fitting and the Monte Carlo simulation — every probability and date.
- Ledger clocks and silent-dropped-commitment detection.
- Tripwire monitors, decision-aging alerts, and critical-path / criticality computation.
- Consent scoping and the audit of what was read.

Numbers never originate in the model. A model output is a claim that passes a deterministic gate
before it can affect a decision, a forecast, or a ledger, and every consequential action is a draft
a human approves.

## Consequences

- **Reproducibility:** because the numbers come from the simulator and the drift engine, the replay
  suite can reproduce every headline result on public data. A reviewer can check us.
- **Auditability:** each claim carries its provenance (source span/quote, model, version, prompt
  hash), so a wrong flag is traceable to whether the sensor or the decision logic failed.
- **Calibrated honesty:** forecasts widen on thin history and say so, rather than emitting a crisp
  number the model has no basis for.
- **Cost:** two layers to build and keep in sync — an extraction/parse layer and a deterministic
  decision layer — instead of one prompt that "just answers." We accept that cost; it is the product.
- **Trust boundary:** the same discipline that keeps the model out of decisions keeps injected
  instructions in ingested content out of them too (see SECURITY.md, LLM01/LLM05).
