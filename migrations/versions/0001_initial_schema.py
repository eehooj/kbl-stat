"""initial KBL, challenge, and Weekly 6 schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-28
"""
from alembic import op

import app.models  # noqa: F401
from app.database import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # Keep this historical revision fixed to its original schema. New models
    # must be created by their own subsequent Alembic revisions.
    tables = [
        table for table in Base.metadata.sorted_tables
        if table.name not in {"season_player_stats", "visible_schedule_games", "team_season_standings"}
    ]
    Base.metadata.create_all(bind, tables=tables)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
