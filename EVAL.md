# EVAL — Parallax

## What "good" means

Parallax is judged on whether its instruments lead reality, not on whether its prose reads well.
Good means: the Drift Index flags an epic *before* the milestone visibly slips; forecasts are
calibrated, not just confident; extraction feeds the ledgers without inventing promises; and every
headline number is reproducible by a stranger on public data. The measurement philosophy is the
product, so the product is measured.

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

## Current status — the harness fails loud on purpose

`scripts/eval.py` (invoked by `make eval`) raises `NotImplementedError("eval harness lands in
Phase 1")`. This is deliberate, per the repo doctrine: an eval harness must raise loudly rather than
pass vacuously. There are **no measured results yet** — the thresholds above are targets the Phase-1
harness will enforce once the drift pipeline and the labeled replay datasets are wired in. Any number
that appears here or in the README before then would be fabricated, and this portfolio does not
fabricate results.

## Acceptance gate

Once implemented, `make eval` is part of the definition of done: a release is blocked if the replay
suite regresses below the committed thresholds. The eval report is published per release so the
numbers are auditable, not asserted.
