# Parallax planted-drift eval report

cases: 4; alert floor: 0.35

case planted-drift: top=checkout (planted checkout) drift=0.7533, control search=0.0000, loose_numbers=[]
case sparse-history: top=api (planted api) drift=0.9000, control docs=0.0000, loose_numbers=[]
case zero-activity: top=core (planted core) drift=0.8000, control infra=0.0000, loose_numbers=[]
case digit-names: top=v2-api (planted v2-api) drift=0.7542, control ui5=0.0000, loose_numbers=[]

| metric | value | bound | pass |
|---|---|---|---|
| drift_detection | 1.0 | >= 1.0 | PASS |
| control_quiet | 1.0 | >= 1.0 | PASS |
| brief_groundedness | 1.0 | >= 1.0 | PASS |
| index_bounds | 1.0 | >= 1.0 | PASS |

key-gated narration section: NOT RUN (no OPENROUTER_API_KEY); deterministic bounds above are the required gate
