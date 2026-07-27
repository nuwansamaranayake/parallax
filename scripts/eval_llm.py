"""Key-gated LLM eval: the real narration stage, measured — never a required CI check,
never a silent skip.

Bounds stated here before the first run:
  citation coverage         = 1.00   every accepted narrative sentence cites at least one
                                     existing stat id and contains no ungrounded number
                                     (re-verified independently of the gate that accepted it)
  accepted fraction         >= 0.50  at least half the generated sentences survive the gate
  repeat-run jaccard        >= 0.60  cited-stat-id stability across two runs on one brief
  paraphrase jaccard        >= 0.60  cited-stat-id stability across a pre-authored brief
                                     paraphrase (the contracts/brief-narration.yaml invariant)

Identity is the app-assigned stat id — deterministic canonical tokens, never model-invented
names (CareerCompiler FAIL-0003: canonicalize before comparing).

Writes eval_report_llm.md. Exits nonzero on a miss (when it runs at all).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groundwork import BaseConfig, LLMGateway  # noqa: E402

from app.engine.brief import build_stats, fmt, render_brief, verify_groundedness  # noqa: E402
from app.engine.drift import compute_drift  # noqa: E402
from app.engine.gitlog import commits_from_entries  # noqa: E402
from app.engine.issues import items_from_entries  # noqa: E402
from app.engine.narrate import narrate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "data" / "synthetic" / "golden" / "golden.json"
REPORT = ROOT / "eval_report_llm.md"

COVERAGE_BOUND = 1.00
ACCEPTED_BOUND = 0.50
JACCARD_BOUND = 0.60


def _jaccard(a: set, b: set) -> float:
    union = a | b
    return (len(a & b) / len(union)) if union else 1.0


def _coverage(narration, stats) -> float:
    """Independent re-check of the accepted narrative (not trusting the gate that built it):
    fraction of accepted sentences that cite only existing stat ids, at least one of them,
    and contain no numeric token outside the stored stat values."""
    if not narration.accepted:
        return 0.0
    ok = 0
    for s in narration.accepted:
        cited_ok = bool(s.stat_ids) and all(sid in stats for sid in s.stat_ids)
        ok += int(cited_ok and verify_groundedness(s.text, stats) == [])
    return ok / len(narration.accepted)


def _paraphrase_brief(stats) -> str:
    """Pre-authored paraphrase of the planted-drift brief: same stats, reworded prose.
    Deterministic — every number still comes from the stat set via fmt()."""
    n = lambda sid: f"{fmt(stats[sid].value)} [{sid}]"  # noqa: E731
    return "\n".join([
        "# Daily project readout — atlas",
        "",
        f"We are tracking {n('project:workstreams')} workstreams with "
        f"{n('project:commits')} commits attributed so far; {n('project:flagged')} "
        f"workstream sits at or beyond the alert floor of {n('project:alert_floor')}.",
        "",
        f"The checkout stream reports {n('ws:checkout:claimed')} of its work complete, "
        f"yet its share of observed activity is only {n('ws:checkout:observed')}: its "
        f"Drift Index stands at {n('ws:checkout:drift')}, on {n('ws:checkout:commits')} "
        f"commit and {n('ws:checkout:churn')} changed lines over "
        f"{n('ws:checkout:items')} tickets.",
        "",
        f"Search shows drift {n('ws:search:drift')} and billing shows "
        f"{n('ws:billing:drift')}; both remain under the floor.",
    ]) + "\n"


def main() -> None:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    model = os.environ.get("LLM_MODEL_EXTRACTION", "")
    if not key or not model:
        print("eval_llm: NOT RUN — OPENROUTER_API_KEY / LLM_MODEL_EXTRACTION missing. "
              "This section is key-gated by design; the deterministic suite in "
              "scripts/eval.py is the required gate.", file=sys.stderr)
        sys.exit(2)

    case = next(c for c in json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
                if c["case_id"] == "planted-drift")
    rows = compute_drift(
        items_from_entries(case["claimed"]),
        commits_from_entries(case["commits"]),
        case["workstreams"],
    )
    base_md, stats = render_brief(case["project"], rows)
    assert build_stats(rows).keys() == stats.keys()

    gw = LLMGateway(BaseConfig(openrouter_api_key=key))
    base = narrate(gw, model, base_md, stats)
    repeat = narrate(gw, model, base_md, stats)
    para = narrate(gw, model, _paraphrase_brief(stats), stats)

    def cited(nr) -> set[str]:
        return {sid for s in nr.accepted for sid in s.stat_ids}

    raw_total = len(base.accepted) + len(base.rejected)
    accepted_fraction = (len(base.accepted) / raw_total) if raw_total else 0.0
    coverage = min(_coverage(base, stats), _coverage(repeat, stats),
                   _coverage(para, stats))
    j_repeat = _jaccard(cited(base), cited(repeat))
    j_para = _jaccard(cited(base), cited(para))

    checks = [
        ("citation coverage (min of 3 runs)", coverage, ">=", COVERAGE_BOUND,
         coverage >= COVERAGE_BOUND),
        ("accepted fraction (base run)", accepted_fraction, ">=", ACCEPTED_BOUND,
         accepted_fraction >= ACCEPTED_BOUND),
        ("repeat-run jaccard (cited stat ids)", j_repeat, ">=", JACCARD_BOUND,
         j_repeat >= JACCARD_BOUND),
        ("paraphrase jaccard (cited stat ids)", j_para, ">=", JACCARD_BOUND,
         j_para >= JACCARD_BOUND),
    ]

    lines = [
        "# Parallax key-gated narration eval",
        "",
        f"model: {model}",
        f"base accepted/rejected: {len(base.accepted)}/{len(base.rejected)}; "
        f"repeat: {len(repeat.accepted)}/{len(repeat.rejected)}; "
        f"paraphrase: {len(para.accepted)}/{len(para.rejected)}",
        f"base cited stat ids: {sorted(cited(base))}",
        "",
        "| metric | value | bound | pass |",
        "|---|---|---|---|",
    ]
    for name, value, op, bound, ok in checks:
        lines.append(f"| {name} | {value:.2f} | {op} {bound} | "
                     f"{'PASS' if ok else 'FAIL'} |")
    lines += ["", f"contract: contracts/brief-narration.yaml (threshold {JACCARD_BOUND})"]
    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if not all(ok for *_x, ok in checks):
        print("EVAL_LLM FAILED", file=sys.stderr)
        sys.exit(1)
    print("EVAL_LLM OK")


if __name__ == "__main__":
    main()
