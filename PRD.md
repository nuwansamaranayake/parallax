# PRD — Parallax

## Users

- **Project / delivery manager (primary).** Owns dates and stakeholder expectations. Needs to know
  when a project is drifting before the board says so, and needs the promises and assumptions made
  in meetings tracked without chasing them by hand.
- **Engineering lead / tech lead.** Wants the drift signal to read breadth (trajectory, review
  latency, cross-signal agreement), not a commit-count leaderboard that punishes honest work.
- **The measured team (every contributor).** Not a passive data source. They can read the measuring
  code, see the signal inventory, and consent to which channels are indexed. Trust is a user
  requirement, not a nicety.
- **The hiring reviewer.** A named audience for this portfolio: someone assessing whether the author
  can build an AI system that keeps humans in the loop and gates consequential output.

## Jobs-to-be-done

1. Tell me where claimed progress and observed activity have diverged, per epic, with the evidence.
2. Turn the plan's dates into calibrated probabilities, not confident single dates.
3. Capture every commitment and assumption made anywhere, quote-anchored, and tell me when one is
   silently dropped or invalidated.
4. Run a standing pre-mortem and compile each risk into a monitor I can actually watch.
5. Draft the nudge so I can edit and send it as myself — never send on my behalf.

## Non-goals

- **Not a ticket system.** Parallax audits the system of record; it does not replace it.
- **Not an autonomous actor.** No auto-sent messages, no self-executing changes. Output is a draft
  for a human. Anything consequential passes a deterministic gate and a human approval.
- **Not an individual-productivity scorer.** No per-person leaderboards, ever. Views are
  aggregate-first; channels are scoped by team consent, not PM fiat.
- **Not a source of numbers from the LLM.** The model classifies and flags qualitative signals; all
  probabilities and drift math come from deterministic code. Where estimate history is thin, the
  forecast widens explicitly rather than printing a crisp but false percentage.

## Success metrics (targets, not yet measured)

Derived from the chapter's evaluation plan and enforced by the Phase-1 eval harness (see
[EVAL.md](EVAL.md)); the harness currently raises `NotImplementedError` on purpose.

- **Drift lead time:** the Drift Index flags an epic a meaningful number of days before the milestone
  visibly slips, at a controlled false-positive rate, measured on replayed public project history.
- **Forecast calibration:** milestone forecasts score well on Brier score and interval coverage
  against realized dates.
- **Extraction quality:** commitment and assumption extraction hits target precision and recall on
  hand-labeled transcripts, tuned to prefer missing a weak promise over inventing one.
- **Tripwire lead time:** compiled tripwires fire ahead of the risks they monitor materializing.
- **Reproducibility:** every headline number in the README is reproducible by a reviewer via the
  public-data replay suite.

## Novelty (scoped)

As of July 2026, we surveyed the open-source project-management and delivery-tracking landscape:
ticket systems, sprint boards, and the AI add-ons that summarize meetings, draft status updates, and
generate subtasks. None of the tools we reviewed makes its core objects the measured gap between
claimed and observed project state, a calibrated probabilistic date forecast built on the team's own
estimate-versus-actual history, and standing ledgers for the promises and assumptions that never
became tickets. That combination, with risks compiled into deterministic tripwires and all signal
collection visible to the measured team, is the bet Parallax makes. This is a scoped claim about the
field we surveyed as of July 2026, not a claim of universal firstness.
