# Parallax key-gated narration eval

model: google/gemini-2.5-flash
base accepted/rejected: 5/0; repeat: 6/0; paraphrase: 4/0
base cited stat ids: ['project:alert_floor', 'project:commits', 'project:flagged', 'project:workstreams', 'ws:billing:claimed', 'ws:billing:drift', 'ws:billing:observed', 'ws:checkout:churn', 'ws:checkout:claimed', 'ws:checkout:commits', 'ws:checkout:drift', 'ws:checkout:items', 'ws:checkout:observed', 'ws:search:churn', 'ws:search:claimed', 'ws:search:commits', 'ws:search:drift', 'ws:search:observed']

| metric | value | bound | pass |
|---|---|---|---|
| citation coverage (min of 3 runs) | 1.00 | >= 1.0 | PASS |
| accepted fraction (base run) | 1.00 | >= 0.5 | PASS |
| repeat-run jaccard (cited stat ids) | 0.90 | >= 0.6 | PASS |
| paraphrase jaccard (cited stat ids) | 0.67 | >= 0.6 | PASS |

contract: contracts/brief-narration.yaml (threshold 0.6)
