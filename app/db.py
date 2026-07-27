"""Schema and session plumbing. metadata is the single source of truth; the alembic
migration applies it, and EXPECTED_TABLE_COUNT asserts the result (Standard 4)."""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

from .config import settings

JSON = sa.JSON().with_variant(JSONB(), "postgresql")

metadata = sa.MetaData()

projects = sa.Table(
    "projects", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

workstreams = sa.Table(
    "workstreams", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
    sa.Column("key", sa.Text, nullable=False),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("path_prefixes", JSON, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

claimed_items = sa.Table(
    "claimed_items", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("workstream_id", sa.Integer, sa.ForeignKey("workstreams.id"), nullable=False),
    sa.Column("item_key", sa.Text, nullable=False),
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("status", sa.Text, nullable=False),           # todo | in_progress | done
    sa.Column("claimed_progress", sa.Float),                # optional tracker assertion
    sa.Column("estimate_points", sa.Float, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

observed_commits = sa.Table(
    "observed_commits", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
    sa.Column("workstream_id", sa.Integer, sa.ForeignKey("workstreams.id")),  # NULL = unattributed
    sa.Column("sha", sa.Text, nullable=False),
    sa.Column("author", sa.Text, nullable=False),
    sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("message", sa.Text, nullable=False),
    sa.Column("files", JSON, nullable=False),
    sa.Column("insertions", sa.Integer, nullable=False),
    sa.Column("deletions", sa.Integer, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

activity_rollups = sa.Table(
    "activity_rollups", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("workstream_id", sa.Integer, sa.ForeignKey("workstreams.id"), nullable=False),
    sa.Column("commit_count", sa.Integer, nullable=False),
    sa.Column("churn", sa.Integer, nullable=False),
    sa.Column("author_count", sa.Integer, nullable=False),
    sa.Column("first_commit_at", sa.DateTime(timezone=True)),
    sa.Column("last_commit_at", sa.DateTime(timezone=True)),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

drift_indices = sa.Table(
    "drift_indices", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("workstream_id", sa.Integer, sa.ForeignKey("workstreams.id"), nullable=False),
    sa.Column("claimed_fraction", sa.Float, nullable=False),
    sa.Column("observed_fraction", sa.Float, nullable=False),
    sa.Column("drift_index", sa.Float, nullable=False),     # in [0, 1]; formula in engine/drift.py
    sa.Column("status", sa.Text, nullable=False),           # scored | completed | unclaimed
    sa.Column("item_count", sa.Integer, nullable=False),
    sa.Column("commit_count", sa.Integer, nullable=False),
    sa.Column("churn", sa.Integer, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

briefs = sa.Table(
    "briefs", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id"), nullable=False),
    sa.Column("markdown", sa.Text, nullable=False),         # deterministic, stat-traced
    sa.Column("narrative", sa.Text),                        # key-gated LLM polish, gated sentences
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

brief_stats = sa.Table(
    "brief_stats", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("brief_id", sa.Integer, sa.ForeignKey("briefs.id"), nullable=False),
    sa.Column("stat_id", sa.Text, nullable=False),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("value", sa.Float, nullable=False),
    sa.Column("rendered", sa.Text, nullable=False),         # exact token in the brief (fmt())
    sa.Column("workstream", sa.Text),                       # NULL for project-level stats
)

_engine = None
_Session = None


def get_engine():
    global _engine, _Session
    if _engine is None:
        _engine = sa.create_engine(settings.database_url, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine)
    return _engine


def get_session():
    get_engine()
    return _Session()


def set_engine_for_tests(engine) -> None:
    """Tests inject their own engine (sqlite in-memory). Explicit, never automatic."""
    global _engine, _Session
    _engine = engine
    _Session = sessionmaker(bind=engine)
