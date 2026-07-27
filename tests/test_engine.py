"""Engine unit tests: connectors, drift math, brief groundedness, narration gate.

Deterministic and keyless. The git-log fixture is constructed inline from the same
separator constants the real `git log` format string uses, so the parser is tested on
byte-identical structure without needing git or a repository.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.engine.brief import build_stats, render_brief, verify_groundedness
from app.engine.drift import ALERT_FLOOR, compute_drift, compute_rollups
from app.engine.gitlog import (
    UNATTRIBUTED, CommitRecord, attribute, commits_from_entries, parse_git_log,
)
from app.engine.issues import claimed_fraction, items_from_entries
from app.engine.narrate import NarrationSentence, gate_sentences

GOLDEN = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "synthetic" / "golden" /
     "golden.json").read_text(encoding="utf-8"))


def _case(case_id: str) -> dict:
    return next(c for c in GOLDEN["cases"] if c["case_id"] == case_id)


def _drift_rows(case: dict):
    return compute_drift(
        items_from_entries(case["claimed"]),
        commits_from_entries(case["commits"]),
        case["workstreams"],
    )


# ---- gitlog connector ----

GITLOG_TEXT = (
    "\x1e" "a1b2c3d4e5f\x1f" "maya\x1f" "2026-07-02T09:15:00+00:00\x1f" "fix tax rounding\n"
    "\n"
    "4\t2\tsrc/checkout/tax.py\n"
    "\x1e" "b2c3d4e5f6a\x1f" "liam\x1f" "2026-07-03T10:00:00+02:00\x1f" "add logo\n"
    "\n"
    "-\t-\tassets/logo.png\n"
    "10\t0\tsrc/search/index.py\n"
    "\x1e" "c3d4e5f6a7b\x1f" "ana\x1f" "2026-07-04T11:00:00+00:00\x1f" "empty merge\n"
)


def test_parse_git_log_records_files_and_churn():
    records = parse_git_log(GITLOG_TEXT)
    assert [r.sha for r in records] == ["a1b2c3d4e5f", "b2c3d4e5f6a", "c3d4e5f6a7b"]
    assert records[0].insertions == 4 and records[0].deletions == 2
    assert records[0].churn == 6
    # binary numstat rows ("-") count zero churn but the file is still recorded
    assert records[1].files == ["assets/logo.png", "src/search/index.py"]
    assert records[1].insertions == 10 and records[1].deletions == 0
    assert records[2].files == [] and records[2].churn == 0
    assert records[1].committed_at.utcoffset().total_seconds() == 7200


def test_commits_from_entries_rejects_malformed():
    with pytest.raises(ValidationError):
        commits_from_entries([{"sha": "short"}])


def test_attribution_explicit_wins_then_prefix_then_unattributed():
    prefixes = {"checkout": ["src/checkout/"], "search": ["src/search/"]}
    explicit = CommitRecord(sha="a" * 7, author="x", committed_at="2026-07-01T00:00:00+00:00",
                            files=["src/checkout/x.py"], workstream="search")
    assert attribute(explicit, prefixes) == "search"
    by_path = CommitRecord(sha="b" * 7, author="x", committed_at="2026-07-01T00:00:00+00:00",
                           files=["src/search/y.py"])
    assert attribute(by_path, prefixes) == "search"
    stray = CommitRecord(sha="c" * 7, author="x", committed_at="2026-07-01T00:00:00+00:00",
                         files=["README.md"])
    assert attribute(stray, prefixes) == UNATTRIBUTED


# ---- claimed model ----

def test_claimed_fraction_is_estimate_weighted():
    items = items_from_entries([
        {"item_key": "A", "workstream": "w", "title": "t", "status": "done",
         "estimate_points": 3},
        {"item_key": "B", "workstream": "w", "title": "t", "status": "todo",
         "estimate_points": 1},
    ])
    assert claimed_fraction(items) == pytest.approx(0.75)


def test_in_progress_without_stated_progress_defaults_to_half():
    items = items_from_entries([
        {"item_key": "A", "workstream": "w", "title": "t", "status": "in_progress"}])
    assert claimed_fraction(items) == pytest.approx(0.5)


def test_malformed_claimed_progress_rejected():
    with pytest.raises(ValidationError):
        items_from_entries([{"item_key": "A", "workstream": "w", "title": "t",
                             "status": "in_progress", "claimed_progress": 1.4}])


# ---- drift engine ----

def test_planted_drifter_ranks_highest_and_control_stays_quiet():
    case = _case("planted-drift")
    rows = _drift_rows(case)
    assert rows[0].workstream == case["planted_drifting"]
    assert rows[0].drift_index >= ALERT_FLOOR
    control = next(r for r in rows if r.workstream == case["healthy_control"])
    assert control.drift_index < ALERT_FLOOR
    for r in rows:
        assert 0.0 <= r.drift_index <= 1.0
        assert 0.0 <= r.claimed_fraction <= 1.0
        assert 0.0 <= r.observed_fraction <= 1.0


def test_zero_activity_project_bounds_and_exclusions():
    rows = _drift_rows(_case("zero-activity"))
    by = {r.workstream: r for r in rows}
    assert by["core"].status == "scored" and by["core"].drift_index == pytest.approx(0.8)
    assert by["legacy"].status == "completed" and by["legacy"].drift_index == 0.0
    assert by["infra"].drift_index == 0.0
    for r in rows:
        assert 0.0 <= r.drift_index <= 1.0


def test_unclaimed_workstream_is_excluded_but_rolled_up():
    prefixes = {"ghost": ["ghost/"]}
    commits = commits_from_entries([
        {"sha": "a" * 7, "author": "x", "committed_at": "2026-07-01T00:00:00+00:00",
         "files": ["ghost/x.py"], "insertions": 5, "deletions": 1}])
    rows = compute_drift([], commits, prefixes)
    assert rows[0].status == "unclaimed" and rows[0].drift_index == 0.0
    assert compute_rollups(commits, prefixes)["ghost"].churn == 6


def test_rollups_keep_unattributed_commits_visible():
    case = _case("planted-drift")
    rollups = compute_rollups(commits_from_entries(case["commits"]), case["workstreams"])
    assert UNATTRIBUTED in rollups and rollups[UNATTRIBUTED].commit_count == 1


# ---- brief ----

def test_brief_is_fully_grounded_and_flags_the_drifter():
    case = _case("planted-drift")
    rows = _drift_rows(case)
    md, stats = render_brief(case["project"], rows)
    assert verify_groundedness(md, stats) == []
    assert "**checkout**" in md
    assert "## Stat trace" in md


def test_groundedness_check_catches_a_loose_number():
    case = _case("planted-drift")
    md, stats = render_brief(case["project"], _drift_rows(case))
    assert verify_groundedness(md + "\nmystery figure 12345 appeared\n", stats) == ["12345"]


def test_brief_renders_identically_twice():
    case = _case("sparse-history")
    md1, _ = render_brief(case["project"], _drift_rows(case))
    md2, _ = render_brief(case["project"], _drift_rows(case))
    assert md1 == md2


# ---- narration gate (deterministic; no LLM) ----

def test_narration_gate_accepts_only_cited_grounded_sentences():
    case = _case("planted-drift")
    rows = _drift_rows(case)
    stats = build_stats(rows)
    drift_txt = f"{stats['ws:checkout:drift'].value:.2f}"
    raw = [
        NarrationSentence(text=f"Checkout claims far more than it shows, drifting at "
                               f"{drift_txt}.", stat_ids=["ws:checkout:drift"]),
        NarrationSentence(text="Everything is fine.", stat_ids=[]),
        NarrationSentence(text="Velocity is 9000.", stat_ids=["ws:checkout:drift"]),
        NarrationSentence(text="Trust me.", stat_ids=["ws:made_up:stat"]),
    ]
    result = gate_sentences(raw, stats)
    assert len(result.accepted) == 1 and result.accepted[0].stat_ids == ["ws:checkout:drift"]
    reasons = [r["reason"] for r in result.rejected]
    assert any("cites no stat ids" in r for r in reasons)
    assert any("ungrounded numbers" in r for r in reasons)
    assert any("unknown stat ids" in r for r in reasons)
