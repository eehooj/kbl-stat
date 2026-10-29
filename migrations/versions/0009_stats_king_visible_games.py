"""store visible StatsKing game cards

Revision ID: 0009_stats_king_visible_games
Revises: 0008_daily_picks_schedule_links
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_stats_king_visible_games"
down_revision = "0008_daily_picks_schedule_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stats_king_visible_games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("observed_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue", sa.String(length=150), nullable=False),
        sa.Column("first_team_name", sa.String(length=100), nullable=False),
        sa.Column("second_team_name", sa.String(length=100), nullable=False),
        sa.Column("participation_status", sa.String(length=50), nullable=False),
        sa.Column("deadline_text", sa.String(length=150), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("stats_king_visible_games")
