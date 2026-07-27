"""The Drift Index: a deterministic diff between the claimed and observed models.

No LLM anywhere in this file. Every number is computed, bounded, and explainable.

THE FORMULA (the contract this module keeps):

    claimed_fraction(w)   estimate-weighted claimed progress of w's tickets, in [0, 1]
                          (engine/issues.claimed_fraction).

    observed_fraction(w)  w's activity relative to the busiest declared workstream:
                              0.5 * commits(w) / max_commits  +  0.5 * churn(w) / max_churn
                          where max_* are taken across declared workstreams. If the project
                          has no commits at all, observed_fraction is 0. If commits exist
                          but total churn is 0 (all zero-churn commits), the churn term is
                          dropped and commit share alone is used. Bounded [0, 1].

    drift_index(w) = max(0, claimed_fraction(w) - observed_fraction(w))

    except: a workstream whose claimed items are ALL done is excluded (drift 0, flagged
    `completed` — finished work needs no activity), and a workstream with NO claimed items
    is excluded (drift 0, flagged `unclaimed` — nothing was claimed, so nothing diverges;
    its observed activity still appears in the rollup).

    Bounded [0, 1] by construction: both fractions live in [0, 1] and max(0, .) clips.

Interpretation: drift is claimed progress that observed activity cannot account for. A
workstream claimed 80% done while showing near-zero activity scores ~0.8; a workstream
whose claimed progress is matched by proportionate activity scores ~0.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .gitlog import UNATTRIBUTED, CommitRecord, attribute
from .issues import ClaimedItem, all_done, claimed_fraction

# A drift index at or above this floor flags the workstream in the brief. The eval's
# healthy control must stay below it (EVAL.md, bounds written before the harness).
ALERT_FLOOR = 0.35


class ActivityRollup(BaseModel):
    """Deterministic per-workstream activity summary (the observed model, aggregated)."""

    workstream: str
    commit_count: int
    churn: int
    author_count: int
    first_commit_at: datetime | None
    last_commit_at: datetime | None


class DriftRow(BaseModel):
    """One workstream's claimed-versus-observed verdict."""

    workstream: str
    claimed_fraction: float
    observed_fraction: float
    drift_index: float
    status: str          # scored | completed | unclaimed
    item_count: int
    commit_count: int
    churn: int


def compute_rollups(
    commits: list[CommitRecord], prefixes: dict[str, list[str]]
) -> dict[str, ActivityRollup]:
    """Aggregate observed activity per declared workstream (+ UNATTRIBUTED when present).

    Every declared workstream gets a rollup even at zero activity — absence of activity is
    the signal this product exists to surface, so it must be a row, not a missing key.
    """
    buckets: dict[str, list[CommitRecord]] = {k: [] for k in prefixes}
    for c in commits:
        buckets.setdefault(attribute(c, prefixes), []).append(c)
    out: dict[str, ActivityRollup] = {}
    for ws, group in buckets.items():
        dates = sorted(c.committed_at for c in group)
        out[ws] = ActivityRollup(
            workstream=ws,
            commit_count=len(group),
            churn=sum(c.churn for c in group),
            author_count=len({c.author for c in group}),
            first_commit_at=dates[0] if dates else None,
            last_commit_at=dates[-1] if dates else None,
        )
    return out


def observed_fraction(rollup: ActivityRollup, max_commits: int, max_churn: int) -> float:
    """The documented observed-activity share, in [0, 1]. See module docstring."""
    if max_commits <= 0:
        return 0.0
    commit_share = rollup.commit_count / max_commits
    if max_churn <= 0:
        return commit_share
    return 0.5 * commit_share + 0.5 * (rollup.churn / max_churn)


def compute_drift(
    items: list[ClaimedItem],
    commits: list[CommitRecord],
    prefixes: dict[str, list[str]],
) -> list[DriftRow]:
    """The deterministic core loop: rollups -> fractions -> Drift Index per workstream.

    Returns one row per declared workstream, sorted by drift_index descending then key
    (stable order — the eval and the brief both depend on it).
    """
    rollups = compute_rollups(commits, prefixes)
    # Fail loud on undeclared workstream names (matching the API's 422 at import): a
    # commit or item naming an unknown workstream would otherwise skew max_* silently
    # (commits) or vanish from the rows (items). UNATTRIBUTED is the one legal extra key.
    unknown = sorted(
        {k for k in rollups if k != UNATTRIBUTED and k not in prefixes}
        | {i.workstream for i in items if i.workstream not in prefixes})
    if unknown:
        raise ValueError(
            f"unknown workstream keys: {unknown} — every commit and claimed item must "
            "name a declared workstream")
    declared = {k: v for k, v in rollups.items() if k in prefixes}
    max_commits = max((r.commit_count for r in declared.values()), default=0)
    max_churn = max((r.churn for r in declared.values()), default=0)

    by_ws: dict[str, list[ClaimedItem]] = {k: [] for k in prefixes}
    for item in items:
        by_ws.setdefault(item.workstream, []).append(item)

    rows: list[DriftRow] = []
    for ws in sorted(prefixes):
        rollup = declared[ws]
        ws_items = by_ws.get(ws, [])
        claimed = claimed_fraction(ws_items)
        observed = observed_fraction(rollup, max_commits, max_churn)
        if not ws_items:
            status, drift = "unclaimed", 0.0
        elif all_done(ws_items):
            status, drift = "completed", 0.0
        else:
            status, drift = "scored", max(0.0, claimed - observed)
        rows.append(DriftRow(
            workstream=ws, claimed_fraction=claimed, observed_fraction=observed,
            drift_index=drift, status=status, item_count=len(ws_items),
            commit_count=rollup.commit_count, churn=rollup.churn))
    rows.sort(key=lambda r: (-r.drift_index, r.workstream))
    return rows
