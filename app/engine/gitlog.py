"""Observed-model connector: commit records, keyless by design.

Two entry paths, both deterministic and both real product features (Standard 3: neither is a
fallback for the other):

1. Structured commit records via JSON (`commits_from_entries`) — what an exporter or a
   webhook would deliver.
2. A local repository path (`read_git_log`) — runs `git log --numstat` and hands the bytes
   to `parse_git_log`, a pure function that is unit-tested on captured fixture text, so the
   parser needs no git and no network in tests.

Workstream attribution is deterministic: an explicit `workstream` key on a record wins;
otherwise the first workstream whose declared path prefix matches a touched file claims the
commit. Unattributed commits are kept and reported, never silently dropped.
"""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator

_RECORD_SEP = "\x1e"   # git log %x1e — record separator between commits
_FIELD_SEP = "\x1f"    # git log %x1f — unit separator between header fields

GIT_LOG_FORMAT = "%x1e%H%x1f%an%x1f%aI%x1f%s"
UNATTRIBUTED = "(unattributed)"


class CommitRecord(BaseModel):
    """One observed commit, attributed to at most one workstream."""

    sha: str = Field(min_length=7)
    author: str = Field(min_length=1)
    committed_at: datetime
    message: str = ""
    files: list[str] = Field(default_factory=list)
    insertions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    workstream: str | None = None   # explicit attribution wins over path matching

    @field_validator("committed_at")
    @classmethod
    def _tz_aware(cls, v: datetime) -> datetime:
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)

    @property
    def churn(self) -> int:
        return self.insertions + self.deletions


def commits_from_entries(entries: list[dict]) -> list[CommitRecord]:
    """JSON import path. Raises on malformed entries — no partial silent acceptance."""
    return [CommitRecord.model_validate(e) for e in entries]


def parse_git_log(text: str) -> list[CommitRecord]:
    """Deterministic parse of `git log --numstat` output in GIT_LOG_FORMAT.

    Pure function: same bytes in, same records out. Binary-file numstat rows ("-") count as
    zero churn but the file is still recorded as touched.
    """
    records: list[CommitRecord] = []
    for chunk in text.split(_RECORD_SEP):
        chunk = chunk.strip("\n\r ")
        if not chunk:
            continue
        header, *body = chunk.splitlines()
        sha, author, iso_date, subject = header.split(_FIELD_SEP, 3)
        files: list[str] = []
        ins = dels = 0
        for line in body:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            a, d, path = parts
            files.append(path)
            if a.isdigit():
                ins += int(a)
            if d.isdigit():
                dels += int(d)
        records.append(CommitRecord(
            sha=sha, author=author, committed_at=datetime.fromisoformat(iso_date),
            message=subject, files=files, insertions=ins, deletions=dels))
    return records


def read_git_log(repo_path: str, timeout: int = 60) -> list[CommitRecord]:
    """Local-repo path: run git, then parse deterministically. Fails loud on a bad repo."""
    r = subprocess.run(
        ["git", "-C", repo_path, "log", f"--pretty=format:{GIT_LOG_FORMAT}", "--numstat"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"git log failed for {repo_path!r}: {r.stderr.strip()[:200]}")
    return parse_git_log(r.stdout)


def attribute(commit: CommitRecord, prefixes: dict[str, list[str]]) -> str:
    """Deterministic workstream attribution. Explicit key wins; then the first workstream
    (sorted by key) with a declared path prefix matching a touched file; else UNATTRIBUTED."""
    if commit.workstream:
        return commit.workstream
    for ws_key in sorted(prefixes):
        for prefix in prefixes[ws_key]:
            if any(f.startswith(prefix) for f in commit.files):
                return ws_key
    return UNATTRIBUTED
