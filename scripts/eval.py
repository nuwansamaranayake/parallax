"""Eval harness: synthetic planted-drift suite against the EVAL.md Phase 1 thresholds.

Deterministic and keyless (JSON connectors, deterministic drift + brief; no LLM, no
network, no timestamps in the report). Writes eval_report.md so consecutive runs can be
compared byte-for-byte. The key-gated narration section (real gateway) is reported
separately by scripts/eval_llm.py and is never a required check — and never a silent skip:
this harness says loudly whether it ran.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.brief import render_brief, verify_groundedness  # noqa: E402
from app.engine.drift import ALERT_FLOOR, compute_drift  # noqa: E402
from app.engine.gitlog import commits_from_entries  # noqa: E402
from app.engine.issues import items_from_entries  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "data" / "synthetic" / "golden" / "golden.json"
REPORT = ROOT / "eval_report.md"

# EVAL.md "Phase 1 acceptance thresholds (written before the harness, 2026-07-27)"
BOUNDS = {
    "drift_detection": 1.00,   # planted drifter ranks highest by Drift Index, every case
    "control_quiet": 1.00,     # healthy control below ALERT_FLOOR, every case
    "brief_groundedness": 1.00,  # every numeric token in every brief matches a stored stat
    "index_bounds": 1.00,      # every drift index (and both fractions) in [0, 1]
}


def main() -> None:
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    cases = data["cases"]

    detect_ok = quiet_ok = grounded_ok = 0
    bounds_total = bounds_ok = 0
    rows_out: list[str] = []

    for case in cases:
        rows = compute_drift(
            items_from_entries(case["claimed"]),
            commits_from_entries(case["commits"]),
            case["workstreams"],
        )
        top = rows[0]
        control = next(r for r in rows if r.workstream == case["healthy_control"])
        detect_ok += int(top.workstream == case["planted_drifting"]
                         and top.drift_index >= ALERT_FLOOR)
        quiet_ok += int(control.drift_index < ALERT_FLOOR)
        for r in rows:
            bounds_total += 3
            bounds_ok += int(0.0 <= r.drift_index <= 1.0)
            bounds_ok += int(0.0 <= r.claimed_fraction <= 1.0)
            bounds_ok += int(0.0 <= r.observed_fraction <= 1.0)
        md, stats = render_brief(case["project"], rows)
        loose = verify_groundedness(md, stats)
        grounded_ok += int(loose == [])
        rows_out.append(
            f"case {case['case_id']}: top={top.workstream} "
            f"(planted {case['planted_drifting']}) drift={top.drift_index:.4f}, "
            f"control {control.workstream}={control.drift_index:.4f}, "
            f"loose_numbers={loose}")

    n = len(cases)
    metrics = {
        "drift_detection": detect_ok / n,
        "control_quiet": quiet_ok / n,
        "brief_groundedness": grounded_ok / n,
        "index_bounds": bounds_ok / bounds_total,
    }
    passes = {k: metrics[k] >= BOUNDS[k] for k in BOUNDS}

    lines = ["# Parallax planted-drift eval report", "",
             f"cases: {n}; alert floor: {ALERT_FLOOR}", ""]
    lines += rows_out + ["", "| metric | value | bound | pass |", "|---|---|---|---|"]
    for k, v in metrics.items():
        lines.append(f"| {k} | {round(v, 4)} | >= {BOUNDS[k]} | "
                     f"{'PASS' if passes[k] else 'FAIL'} |")
    if os.environ.get("OPENROUTER_API_KEY"):
        lines += ["", "key-gated narration section: run scripts/eval_llm.py "
                      "(not part of this deterministic report)"]
    else:
        lines += ["", "key-gated narration section: NOT RUN (no OPENROUTER_API_KEY); "
                      "deterministic bounds above are the required gate"]
    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if not all(passes.values()):
        print("EVAL FAILED: at least one threshold missed (see rows above)", file=sys.stderr)
        sys.exit(1)
    print("EVAL OK")


if __name__ == "__main__":
    main()
