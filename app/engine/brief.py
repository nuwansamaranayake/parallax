"""The morning brief: deterministic markdown assembled ONLY from computed statistics.

Every number that appears in the brief is emitted through `_num`, which renders the value
followed by its stat id in brackets — the trace is part of the document, not an afterthought.
A "Stat trace" section at the bottom lists every stat. `verify_groundedness` parses the
rendered markdown and checks that every numeric token matches a stored stat value; the eval
harness enforces it at 1.0 (EVAL.md, bounds written before the harness).

Stat ids are deterministic app-assigned tokens (`ws:<key>:<metric>`, `project:<metric>`),
never model-invented names (CareerCompiler FAIL-0003: canonicalize before comparing).
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from .drift import ALERT_FLOOR, DriftRow

_NUMERIC = re.compile(r"\d+(?:\.\d+)?")
# A stat-id marker: bracketed, starts with a letter. Stripped before groundedness scanning
# so ids themselves are never mistaken for numbers.
_MARKER = re.compile(r"\[(?=[a-z])[a-z0-9_:.\-]+\]")


class Stat(BaseModel):
    """One stored statistic: the only thing a brief number is allowed to be."""

    stat_id: str
    name: str
    value: float | int
    workstream: str | None = None


def fmt(value: float | int) -> str:
    """Canonical rendering: ints plain, floats at 2 decimals. One format everywhere, so
    the groundedness check is exact string matching, not tolerance arithmetic."""
    if isinstance(value, bool):  # bools are ints in Python; refuse the ambiguity
        raise TypeError("stat values must be numbers, not booleans")
    return str(value) if isinstance(value, int) else f"{value:.2f}"


def build_stats(rows: list[DriftRow]) -> dict[str, Stat]:
    """Compute the full stat set for a project's drift rows. Deterministic order and ids."""
    stats: dict[str, Stat] = {}

    def put(stat_id: str, name: str, value: float | int, workstream: str | None = None):
        stats[stat_id] = Stat(stat_id=stat_id, name=name, value=value, workstream=workstream)

    flagged = [r for r in rows if r.status == "scored" and r.drift_index >= ALERT_FLOOR]
    put("project:alert_floor", "alert floor", ALERT_FLOOR)
    put("project:workstreams", "workstream count", len(rows))
    put("project:flagged", "flagged workstream count", len(flagged))
    put("project:commits", "total attributed commits", sum(r.commit_count for r in rows))
    for r in rows:
        k = r.workstream
        put(f"ws:{k}:claimed", "claimed progress fraction", r.claimed_fraction, k)
        put(f"ws:{k}:observed", "observed activity fraction", r.observed_fraction, k)
        put(f"ws:{k}:drift", "drift index", r.drift_index, k)
        put(f"ws:{k}:commits", "commit count", r.commit_count, k)
        put(f"ws:{k}:churn", "file churn (lines)", r.churn, k)
        put(f"ws:{k}:items", "claimed item count", r.item_count, k)
    return stats


def _num(stats: dict[str, Stat], stat_id: str) -> str:
    """The only legal way a number enters the brief: value + traceable stat id."""
    return f"{fmt(stats[stat_id].value)} [{stat_id}]"


def render_brief(project_name: str, rows: list[DriftRow]) -> tuple[str, dict[str, Stat]]:
    """Deterministic markdown. No timestamps, no prose numbers, no LLM. Rows arrive sorted
    by drift descending (compute_drift's contract), so the layout is stable byte-for-byte."""
    stats = build_stats(rows)
    n = lambda sid: _num(stats, sid)  # noqa: E731
    flagged = [r for r in rows if r.status == "scored" and r.drift_index >= ALERT_FLOOR]

    lines = [
        f"# Morning Brief — {project_name}",
        "",
        "Deterministic brief: every number below carries its stat id in brackets and is",
        "listed again in the Stat trace section. Nothing here came from a language model.",
        "",
        f"Workstreams tracked: {n('project:workstreams')}. Attributed commits: "
        f"{n('project:commits')}. Flagged: {n('project:flagged')} (drift at or above the "
        f"alert floor {n('project:alert_floor')}).",
        "",
        "## Flagged workstreams",
        "",
    ]
    if flagged:
        for r in flagged:
            k = r.workstream
            lines.append(
                f"- **{k}**: claimed {n(f'ws:{k}:claimed')} done, but its observed activity "
                f"share is {n(f'ws:{k}:observed')} — Drift Index {n(f'ws:{k}:drift')} from "
                f"{n(f'ws:{k}:commits')} commits / {n(f'ws:{k}:churn')} churned lines across "
                f"{n(f'ws:{k}:items')} claimed items.")
    else:
        lines.append(f"- none — every scored workstream sits below the alert floor "
                     f"{n('project:alert_floor')}.")
    lines += ["", "## All workstreams",
              "", "| workstream | status | claimed | observed | drift | commits | churn |",
              "|---|---|---|---|---|---|---|"]
    for r in rows:
        k = r.workstream
        lines.append(
            f"| {k} | {r.status} | {n(f'ws:{k}:claimed')} | {n(f'ws:{k}:observed')} | "
            f"{n(f'ws:{k}:drift')} | {n(f'ws:{k}:commits')} | {n(f'ws:{k}:churn')} |")
    lines += ["", "## Stat trace", ""]
    for sid in sorted(stats):
        s = stats[sid]
        scope = f"workstream {s.workstream}" if s.workstream else "project"
        lines.append(f"- [{sid}] {s.name} ({scope}) = {fmt(s.value)}")
    return "\n".join(lines) + "\n", stats


def verify_groundedness(markdown: str, stats: dict[str, Stat]) -> list[str]:
    """Parse the brief and return every numeric token that does NOT match a stored stat
    value (empty list = fully grounded). Stat-id markers are stripped before scanning."""
    allowed = {fmt(s.value) for s in stats.values()}
    body = _MARKER.sub("", markdown)
    return [tok for tok in _NUMERIC.findall(body) if tok not in allowed]
