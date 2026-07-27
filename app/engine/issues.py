"""Claimed-model connector: issue-tracker records via JSON, keyless by design.

Tickets are claims, not facts — that is the whole thesis. Each record carries what the
tracker asserts: a status, an optional claimed progress fraction, an optional estimate.
This module types those assertions; nothing here judges them (the drift engine does).

The claimed progress fraction per workstream is deterministic and documented:

    done         -> 1.0
    in_progress  -> claimed_progress if the ticket states one, else 0.5
    todo         -> 0.0

    claimed_fraction(workstream) = sum(progress_i * weight_i) / sum(weight_i)

where weight_i is the ticket's estimate_points (default 1.0 when the tracker gives none).
Bounded [0, 1] by construction.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ItemStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class ClaimedItem(BaseModel):
    """One ticket-shaped claim from the tracker export."""

    item_key: str = Field(min_length=1)
    workstream: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: ItemStatus
    claimed_progress: float | None = Field(default=None, ge=0.0, le=1.0)
    estimate_points: float = Field(default=1.0, gt=0.0)

    @property
    def progress(self) -> float:
        if self.status is ItemStatus.done:
            return 1.0
        if self.status is ItemStatus.todo:
            return 0.0
        return self.claimed_progress if self.claimed_progress is not None else 0.5


def items_from_entries(entries: list[dict]) -> list[ClaimedItem]:
    """JSON import path. Raises on malformed entries — no partial silent acceptance."""
    return [ClaimedItem.model_validate(e) for e in entries]


def claimed_fraction(items: list[ClaimedItem]) -> float:
    """Estimate-weighted claimed progress for one workstream's items, in [0, 1]."""
    if not items:
        return 0.0
    total = sum(i.estimate_points for i in items)
    return sum(i.progress * i.estimate_points for i in items) / total


def all_done(items: list[ClaimedItem]) -> bool:
    return bool(items) and all(i.status is ItemStatus.done for i in items)
