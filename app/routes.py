"""Business endpoints: the claimed/observed -> drift -> brief loop, persisted.

POST /api/v1/projects                              create project + workstreams
POST /api/v1/projects/{id}/claimed/import          issue-tracker JSON import (keyless)
POST /api/v1/projects/{id}/observed/import         commit-record JSON import (keyless)
POST /api/v1/projects/{id}/drift/compute           deterministic rollups + Drift Index, persisted
GET  /api/v1/projects/{id}/drift                   stored drift rows, sorted by drift desc
GET  /api/v1/workstreams/{id}/drift                one workstream's stored row + rollup
POST /api/v1/projects/{id}/brief                   deterministic brief + stats, persisted
GET  /api/v1/projects/{id}/brief                   latest stored brief with its stat trace
POST /api/v1/briefs/{id}/narrate                   LLM narration polish (key-gated)

The whole core loop is keyless and deterministic — that is the product, not a fallback.
The narration endpoint refuses loudly without a key (typed 503, Standard 3). Recomputing
drift replaces the project's previous rollup/index rows (current-state semantics; history
arrives in Phase 2). Bearer auth on mutations when SMOKE_TEST_TOKEN is set.
"""
from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Header, HTTPException
from groundwork import BaseConfig, LLMGateway
from pydantic import BaseModel, Field

from . import db
from .config import settings
from .engine.brief import Stat, fmt, render_brief
from .engine.drift import DriftRow, compute_drift, compute_rollups
from .engine.gitlog import UNATTRIBUTED, CommitRecord, attribute, commits_from_entries
from .engine.issues import ClaimedItem, items_from_entries
from .engine.narrate import narrate

router = APIRouter(prefix="/api/v1")


def _auth(authorization: str | None) -> None:
    token = settings.smoke_test_token
    if token and authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="missing or invalid bearer token")


def _gateway() -> LLMGateway:
    if not settings.openrouter_api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM narration requires OPENROUTER_API_KEY; the deterministic brief at "
                   "GET /api/v1/projects/{id}/brief is the keyless product",
        )
    gw = LLMGateway(BaseConfig(
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_base_url=settings.openrouter_base_url,
    ))
    # groundwork's gateway does not yet expose a timeout knob and the OpenAI client
    # default is 600s — long enough to pin a worker. Bound every call here from
    # LLM_TIMEOUT_SECONDS (with_options returns a client copy with the timeout applied).
    gw._client = gw._client.with_options(timeout=settings.llm_timeout_seconds)
    return gw


def _ws_map(s, project_id: int) -> dict[str, int]:
    """workstream key -> id for a project; empty dict when the project has none."""
    rows = s.execute(sa.select(db.workstreams.c.key, db.workstreams.c.id)
                     .where(db.workstreams.c.project_id == project_id)).all()
    return {k: i for k, i in rows}


def _prefixes(s, project_id: int) -> dict[str, list[str]]:
    rows = s.execute(sa.select(db.workstreams.c.key, db.workstreams.c.path_prefixes)
                     .where(db.workstreams.c.project_id == project_id)).all()
    return {k: list(p or []) for k, p in rows}


def _require_project(s, project_id: int) -> None:
    if not s.execute(sa.select(db.projects.c.id)
                     .where(db.projects.c.id == project_id)).first():
        raise HTTPException(status_code=404, detail="project not found")


def _load_domain(s, project_id: int) -> tuple[list[ClaimedItem], list[CommitRecord]]:
    """Rebuild typed engine inputs from stored rows. Attribution was resolved at import
    time and is carried on each commit explicitly (deterministic, stored once)."""
    ws_rows = s.execute(sa.select(db.workstreams.c.id, db.workstreams.c.key)
                        .where(db.workstreams.c.project_id == project_id)).all()
    key_by_id = {i: k for i, k in ws_rows}
    item_rows = s.execute(sa.select(db.claimed_items)
                          .where(db.claimed_items.c.workstream_id.in_(key_by_id))
                          ).mappings().all()
    items = [ClaimedItem(
        item_key=r["item_key"], workstream=key_by_id[r["workstream_id"]],
        title=r["title"], status=r["status"], claimed_progress=r["claimed_progress"],
        estimate_points=r["estimate_points"]) for r in item_rows]
    commit_rows = s.execute(sa.select(db.observed_commits)
                            .where(db.observed_commits.c.project_id == project_id)
                            ).mappings().all()
    commits = [CommitRecord(
        sha=r["sha"], author=r["author"], committed_at=r["committed_at"],
        message=r["message"], files=list(r["files"] or []),
        insertions=r["insertions"], deletions=r["deletions"],
        workstream=key_by_id.get(r["workstream_id"])) for r in commit_rows]
    return items, commits


class WorkstreamIn(BaseModel):
    key: str = Field(min_length=1)
    name: str | None = None
    paths: list[str] = Field(default_factory=list)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1)
    workstreams: list[WorkstreamIn] = Field(min_length=1)


class ClaimedImportIn(BaseModel):
    items: list[dict] = Field(min_length=1)


class ObservedImportIn(BaseModel):
    commits: list[dict] = Field(min_length=1)


@router.post("/projects", status_code=201)
def create_project(body: ProjectIn, authorization: str | None = Header(default=None)):
    _auth(authorization)
    keys = [w.key for w in body.workstreams]
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=422, detail="workstream keys must be unique")
    with db.get_session() as s, s.begin():
        pid = s.execute(db.projects.insert().values(name=body.name)).inserted_primary_key[0]
        for w in body.workstreams:
            s.execute(db.workstreams.insert().values(
                project_id=pid, key=w.key, name=w.name or w.key, path_prefixes=w.paths))
    return {"project_id": pid, "workstreams": len(body.workstreams)}


@router.post("/projects/{pid}/claimed/import", status_code=201)
def import_claimed(pid: int, body: ClaimedImportIn,
                   authorization: str | None = Header(default=None)):
    _auth(authorization)
    try:
        items = items_from_entries(body.items)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    with db.get_session() as s, s.begin():
        _require_project(s, pid)
        ws = _ws_map(s, pid)
        unknown = sorted({i.workstream for i in items} - set(ws))
        if unknown:
            raise HTTPException(status_code=422,
                                detail=f"unknown workstream keys: {unknown}")
        for i in items:
            s.execute(db.upsert(s.get_bind(), db.claimed_items, dict(
                workstream_id=ws[i.workstream], item_key=i.item_key, title=i.title,
                status=i.status.value, claimed_progress=i.claimed_progress,
                estimate_points=i.estimate_points),
                ["workstream_id", "item_key"]))
    return {"imported": len(items)}


@router.post("/projects/{pid}/observed/import", status_code=201)
def import_observed(pid: int, body: ObservedImportIn,
                    authorization: str | None = Header(default=None)):
    _auth(authorization)
    try:
        commits = commits_from_entries(body.commits)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    with db.get_session() as s, s.begin():
        _require_project(s, pid)
        ws = _ws_map(s, pid)
        prefixes = _prefixes(s, pid)
        attributed = unattributed = 0
        for c in commits:
            target = attribute(c, prefixes)
            if target != UNATTRIBUTED and target not in ws:
                raise HTTPException(status_code=422,
                                    detail=f"unknown workstream key: {target!r}")
            wid = ws.get(target)
            attributed += int(wid is not None)
            unattributed += int(wid is None)
            s.execute(db.upsert(s.get_bind(), db.observed_commits, dict(
                project_id=pid, workstream_id=wid, sha=c.sha, author=c.author,
                committed_at=c.committed_at, message=c.message, files=c.files,
                insertions=c.insertions, deletions=c.deletions),
                ["project_id", "sha"]))
    return {"imported": len(commits), "attributed": attributed,
            "unattributed": unattributed}


@router.post("/projects/{pid}/drift/compute", status_code=201)
def compute_project_drift(pid: int, authorization: str | None = Header(default=None)):
    _auth(authorization)
    with db.get_session() as s, s.begin():
        _require_project(s, pid)
        ws = _ws_map(s, pid)
        prefixes = _prefixes(s, pid)
        items, commits = _load_domain(s, pid)
        if not items and not commits:
            raise HTTPException(status_code=422,
                                detail="nothing imported yet: import claimed items and/or "
                                       "observed commits first")
        rows = compute_drift(items, commits, prefixes)
        rollups = compute_rollups(commits, prefixes)
        wids = list(ws.values())
        s.execute(db.drift_indices.delete()
                  .where(db.drift_indices.c.workstream_id.in_(wids)))
        s.execute(db.activity_rollups.delete()
                  .where(db.activity_rollups.c.workstream_id.in_(wids)))
        # Upserts (unique index per workstream): two concurrent computes converge on one
        # row per workstream instead of double-inserting under READ COMMITTED.
        for key, rollup in rollups.items():
            if key == UNATTRIBUTED:
                continue
            s.execute(db.upsert(s.get_bind(), db.activity_rollups, dict(
                workstream_id=ws[key], commit_count=rollup.commit_count,
                churn=rollup.churn, author_count=rollup.author_count,
                first_commit_at=rollup.first_commit_at,
                last_commit_at=rollup.last_commit_at),
                ["workstream_id"]))
        for r in rows:
            s.execute(db.upsert(s.get_bind(), db.drift_indices, dict(
                workstream_id=ws[r.workstream], claimed_fraction=r.claimed_fraction,
                observed_fraction=r.observed_fraction, drift_index=r.drift_index,
                status=r.status, item_count=r.item_count, commit_count=r.commit_count,
                churn=r.churn),
                ["workstream_id"]))
    return {"computed": len(rows),
            "rows": [r.model_dump() for r in rows]}


def _stored_drift_rows(s, pid: int) -> list[DriftRow]:
    rows = s.execute(
        sa.select(db.drift_indices, db.workstreams.c.key)
        .join(db.workstreams, db.drift_indices.c.workstream_id == db.workstreams.c.id)
        .where(db.workstreams.c.project_id == pid)).mappings().all()
    out = [DriftRow(
        workstream=r["key"], claimed_fraction=r["claimed_fraction"],
        observed_fraction=r["observed_fraction"], drift_index=r["drift_index"],
        status=r["status"], item_count=r["item_count"], commit_count=r["commit_count"],
        churn=r["churn"]) for r in rows]
    out.sort(key=lambda r: (-r.drift_index, r.workstream))
    return out


@router.get("/projects/{pid}/drift")
def get_project_drift(pid: int, authorization: str | None = Header(default=None)):
    _auth(authorization)
    with db.get_session() as s:
        _require_project(s, pid)
        rows = _stored_drift_rows(s, pid)
        if not rows:
            raise HTTPException(status_code=404,
                                detail="no drift computed yet: POST .../drift/compute")
    return {"project_id": pid, "rows": [r.model_dump() for r in rows]}


@router.get("/workstreams/{wid}/drift")
def get_workstream_drift(wid: int, authorization: str | None = Header(default=None)):
    _auth(authorization)
    with db.get_session() as s:
        row = s.execute(sa.select(db.drift_indices)
                        .where(db.drift_indices.c.workstream_id == wid)).mappings().first()
        if row is None:
            raise HTTPException(status_code=404,
                                detail="no drift stored for this workstream")
        rollup = s.execute(sa.select(db.activity_rollups)
                           .where(db.activity_rollups.c.workstream_id == wid)
                           ).mappings().first()
    return {"drift": dict(row), "rollup": dict(rollup) if rollup else None}


@router.post("/projects/{pid}/brief", status_code=201)
def create_brief(pid: int, authorization: str | None = Header(default=None)):
    _auth(authorization)
    with db.get_session() as s, s.begin():
        _require_project(s, pid)
        name = s.execute(sa.select(db.projects.c.name)
                         .where(db.projects.c.id == pid)).scalar_one()
        rows = _stored_drift_rows(s, pid)
        if not rows:
            raise HTTPException(status_code=422,
                                detail="no drift computed yet: POST .../drift/compute")
        markdown, stats = render_brief(name, rows)
        bid = s.execute(db.briefs.insert().values(
            project_id=pid, markdown=markdown)).inserted_primary_key[0]
        for stat in stats.values():
            s.execute(db.brief_stats.insert().values(
                brief_id=bid, stat_id=stat.stat_id, name=stat.name,
                value=float(stat.value), rendered=fmt(stat.value),
                workstream=stat.workstream))
    return {"brief_id": bid, "stats": len(stats), "markdown": markdown}


def _load_brief(s, bid: int) -> tuple[dict, dict[str, Stat]]:
    brief = s.execute(sa.select(db.briefs)
                      .where(db.briefs.c.id == bid)).mappings().first()
    if brief is None:
        raise HTTPException(status_code=404, detail="brief not found")
    stat_rows = s.execute(sa.select(db.brief_stats)
                          .where(db.brief_stats.c.brief_id == bid)).mappings().all()
    stats = {}
    for r in stat_rows:
        # `rendered` preserves the exact token that appears in the brief, so int/float
        # formatting round-trips through the database without drifting.
        value = float(r["rendered"]) if "." in r["rendered"] else int(r["rendered"])
        stats[r["stat_id"]] = Stat(stat_id=r["stat_id"], name=r["name"], value=value,
                                   workstream=r["workstream"])
    return dict(brief), stats


@router.get("/projects/{pid}/brief")
def get_latest_brief(pid: int, authorization: str | None = Header(default=None)):
    _auth(authorization)
    with db.get_session() as s:
        _require_project(s, pid)
        row = s.execute(sa.select(db.briefs.c.id)
                        .where(db.briefs.c.project_id == pid)
                        .order_by(db.briefs.c.id.desc())).first()
        if row is None:
            raise HTTPException(status_code=404,
                                detail="no brief yet: POST .../brief")
        brief, stats = _load_brief(s, row.id)
    return {"brief": brief, "stats": [s_.model_dump() for s_ in stats.values()]}


@router.post("/briefs/{bid}/narrate", status_code=201)
def narrate_brief(bid: int, authorization: str | None = Header(default=None)):
    _auth(authorization)
    gateway = _gateway()
    # Phase 1 pins narration to the extraction-model slot: the model with observed
    # strict-schema enforcement (CareerCompiler FAIL-0003 — capability flags lie,
    # observed behavior wins). Model ID comes from config, never hardcoded — and an
    # unset slot refuses loudly with the same typed 503 pattern as a missing key.
    if not settings.llm_model_extraction:
        raise HTTPException(
            status_code=503,
            detail="LLM narration requires LLM_MODEL_EXTRACTION (narration model slot); "
                   "the deterministic brief at GET /api/v1/projects/{id}/brief is the "
                   "keyless product",
        )
    # Read transaction: load inputs, then release the connection. The LLM network call
    # must never run inside an open DB transaction — a slow provider would pin pooled
    # connections and starve every other endpoint.
    with db.get_session() as s:
        brief, stats = _load_brief(s, bid)
    result = narrate(gateway, settings.llm_model_extraction, brief["markdown"], stats)
    # Write transaction: store the gated narrative.
    with db.get_session() as s, s.begin():
        s.execute(db.briefs.update().where(db.briefs.c.id == bid)
                  .values(narrative=result.text))
    return {"brief_id": bid, "narrative": result.text,
            "accepted": [x.model_dump() for x in result.accepted],
            "rejected": result.rejected}
