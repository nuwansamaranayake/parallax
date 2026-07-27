"""CLI morning brief: keyless, serverless, deterministic.

Usage:
    python -m app.cli brief --data data/synthetic/golden/golden.json --case planted-drift
                            [--report out.md]
    python -m app.cli ingest-git --repo path/to/repo [--json out.json]

`brief` runs the full claimed/observed -> drift -> brief loop in memory from a golden-format
JSON file, prints the grounded brief, and exits nonzero when any workstream is flagged at or
above the alert floor — so a script (or a cron job) can branch on drift.

`ingest-git` is the local-repo connector: it runs `git log --numstat`, parses it
deterministically, and emits commit records as JSON ready for the observed-import endpoint.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine.brief import render_brief
from .engine.drift import ALERT_FLOOR, compute_drift
from .engine.gitlog import commits_from_entries, read_git_log
from .engine.issues import items_from_entries


def brief(data_path: str, case_id: str, report_path: str | None) -> int:
    data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    case = next((c for c in data["cases"] if c["case_id"] == case_id), None)
    if case is None:
        print(f"unknown case '{case_id}'; available: "
              f"{[c['case_id'] for c in data['cases']]}", file=sys.stderr)
        return 2
    rows = compute_drift(
        items_from_entries(case["claimed"]),
        commits_from_entries(case["commits"]),
        case["workstreams"],
    )
    text, _stats = render_brief(case["project"], rows)
    if report_path:
        Path(report_path).write_text(text, encoding="utf-8", newline="\n")
    print(text)
    flagged = [r for r in rows if r.status == "scored" and r.drift_index >= ALERT_FLOOR]
    return 1 if flagged else 0


def ingest_git(repo: str, json_path: str | None) -> int:
    records = read_git_log(repo)
    payload = [json.loads(r.model_dump_json()) for r in records]
    text = json.dumps({"commits": payload}, indent=2)
    if json_path:
        Path(json_path).write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {len(records)} commit records to {json_path}")
    else:
        print(text)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(prog="parallax")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("brief", help="run the drift loop and print the grounded brief")
    b.add_argument("--data", required=True)
    b.add_argument("--case", required=True)
    b.add_argument("--report", default=None)
    g = sub.add_parser("ingest-git", help="parse a local repo's git log into commit records")
    g.add_argument("--repo", required=True)
    g.add_argument("--json", default=None)
    args = ap.parse_args()
    if args.cmd == "brief":
        sys.exit(brief(args.data, args.case, args.report))
    sys.exit(ingest_git(args.repo, args.json))


if __name__ == "__main__":
    main()
