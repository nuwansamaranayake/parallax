"""Unique indexes for idempotent imports and single-row-per-workstream drift state.

Revision ID: 0003_idempotent_imports
Revises: 0002_real_schema
Create Date: 2026-07-27

Re-delivered tracker exports and commit payloads must upsert, not duplicate (a re-import
after todo->done was double-counting claims; a re-posted commit doubled churn), and two
concurrent drift computes must converge on one row per workstream. Duplicates that predate
the constraints are collapsed keeping the newest row (max id) — the row the latest import
wrote. Indexes are created with IF NOT EXISTS because migration 0002 applies
`app.db.metadata` via create_all, so a fresh database already has them. Table count is
unchanged: EXPECTED_TABLE_COUNT stays 9 (Standard 4).
"""
from alembic import op

revision = "0003_idempotent_imports"
down_revision = "0002_real_schema"
branch_labels = None
depends_on = None

_DEDUPE = [
    """DELETE FROM claimed_items a USING claimed_items b
       WHERE a.workstream_id = b.workstream_id AND a.item_key = b.item_key AND a.id < b.id""",
    """DELETE FROM observed_commits a USING observed_commits b
       WHERE a.project_id = b.project_id AND a.sha = b.sha AND a.id < b.id""",
    """DELETE FROM activity_rollups a USING activity_rollups b
       WHERE a.workstream_id = b.workstream_id AND a.id < b.id""",
    """DELETE FROM drift_indices a USING drift_indices b
       WHERE a.workstream_id = b.workstream_id AND a.id < b.id""",
]

_INDEXES = {
    "uq_claimed_items_workstream_item": "claimed_items (workstream_id, item_key)",
    "uq_observed_commits_project_sha": "observed_commits (project_id, sha)",
    "uq_activity_rollups_workstream": "activity_rollups (workstream_id)",
    "uq_drift_indices_workstream": "drift_indices (workstream_id)",
}


def upgrade() -> None:
    for sql in _DEDUPE:
        op.execute(sql)
    for name, target in _INDEXES.items():
        op.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {target}")


def downgrade() -> None:
    for name in _INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
