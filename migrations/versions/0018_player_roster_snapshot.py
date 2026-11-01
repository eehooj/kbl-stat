"""mark complete visible player roster snapshots

Revision ID: 0018_roster_snapshot
Revises: 0017_special_scoring
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0018_roster_snapshot"
down_revision = "0017_special_scoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "visible_player_season_stats",
        sa.Column("roster_snapshot_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("visible_player_season_stats", "roster_snapshot_at")
