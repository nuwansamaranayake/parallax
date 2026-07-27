# EVAL — Parallax

## What "good" means

Parallax is judged on whether its instruments lead reality, not on whether its prose reads well.
Good means: the Drift Index flags an epic *before* the milestone visibly slips; forecasts are
calibrated, not just confident; extraction feeds the ledgers without inventing promises; and every
headline number is reproducible by a stranger on public data. The measurement philosophy is the
product, so the product is measured.

## Phase 1 acceptance thresholds (written before the harness, 2026-07-27)

Phase 1 ships the drift core (git-log + issue-tracker JSON connectors, Claimed and Observed
models, deterministic Drift Index, deterministic morning brief — LLM narration is key-gated
polish). The suite is deterministic and keyless: synthetic project histories with planted
drift (a workstream claimed 80% done with near-zero observed activity) and a healthy control,
plus edge cases (zero-activity project, fully-done workstream). `scripts/eval.py` exits
nonzero on any miss.

| Metric | Definition | Bound |
|---|---|---|
| Drift detection | the planted drifting workstream ranks highest by Drift Index in every case | = 1.00 |
| Control quiet | the healthy control stays below the alert floor (0.35) in every case | = 1.00 |
| Brief groundedness | every numeric token in the rendered brief matches a stored stat value | = 1.00 |
| Index bounds | every computed Drift Index lies in [0, 1], including edge cases | = 1.00 |
| Reproducibility | two consecutive `make eval` runs | identical reports |

Narration quality (LLM stage) is measured separately and key-gated — `scripts/eval_llm.py`
through the real gateway, bounds stated in that file before its first run: every accepted
narrative sentence cites at least one existing stat id (citation coverage = 1.00), at least
half the generated sentences survive the citation gate, and cited-stat sets stay stable
across a pre-authored brief paraphrase (jaccard >= 0.6 — the
`contracts/brief-narration.yaml` invariant). Reported when a key is present, never a
required keyless check, and never silently skipped. The replay bounds below (lead time,
Brier, ledgers, tripwires) join in Phase 2/3 with the code they measure.

## How `make eval` will measure it

Evaluation is **replay-based**: Parallax runs over the public history of a real open-source project
(repository plus issue tracker, replayed month by month), and its outputs are scored against what
actually happened. The suite ships in the repo against public datasets so every result is
reproducible — no private data, no unfalsifiable claims.

| Capability | Metric | Target (goal, not an achieved result) |
|---|---|---|
| Drift Index | Lead time in days before the actual slip, at a controlled false-positive rate | Leads real slips by a materially useful margin; FPR held under threshold |
| Milestone forecast | Brier score + prediction-interval coverage vs realized dates | Well-calibrated; coverage matches nominal interval |
| Commitment extraction | Precision / recall on hand-labeled transcripts | High precision (prefer a miss over a fabrication) with usable recall |
| Assumption extraction | Precision / recall + valid invalidation-signal rate | Every accepted assumption carries an observable invalidation signal |
| Tripwire monitors | Lead time vs materialized risk | Fires ahead of the risk becoming visible |
| Extraction / brief stability | Consistency across reruns (Seismograph-monitored) | Stable claims and brief text under fixed inputs |

## Current status

The Phase 1 harness is real: `scripts/eval.py` enforces the acceptance table above and exits
nonzero on any miss. The bounds were committed before the harness existed (bounds-first, per
doctrine). First published run 2026-07-27: all four bounds PASS at 1.0 (planted drifter
ranked highest in every case at drift 0.7533 / 0.9000 / 0.8000; controls at 0.0), report
byte-reproducible across consecutive runs (`eval_report.md`). The key-gated narration
section (`scripts/eval_llm.py`) writes `eval_report_llm.md` when a key is present and states
loudly when it did not run. The replay thresholds in the table below remain Phase 2/3
targets, not achieved results.

## Acceptance gate

Once implemented, `make eval` is part of the definition of done: a release is blocked if the replay
suite regresses below the committed thresholds. The eval report is published per release so the
numbers are auditable, not asserted.
