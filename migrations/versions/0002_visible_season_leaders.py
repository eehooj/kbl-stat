"""store browser-rendered season leader snapshots

Revision ID: 0002_visible_leaders
Revises: 0001_initial
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_visible_leaders"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "season_player_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.String(length=100), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("season_id", "metric", "player_name", "team_name", name="uq_season_leader_player"),
    )


def downgrade() -> None:
    op.drop_table("season_player_stats")
