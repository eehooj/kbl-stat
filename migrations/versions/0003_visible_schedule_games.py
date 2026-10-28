"""add rendered schedule observations

Revision ID: 0003_visible_schedule_games
Revises: 0002_visible_season_leaders
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0003_visible_schedule_games"
down_revision = "0002_visible_leaders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visible_schedule_games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("observed_key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("competition", sa.String(length=50), nullable=False),
        sa.Column("venue", sa.String(length=150), nullable=False),
        sa.Column("first_team_name", sa.String(length=100), nullable=False),
        sa.Column("second_team_name", sa.String(length=100), nullable=False),
        sa.Column("first_score", sa.Integer(), nullable=True),
        sa.Column("second_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("visible_schedule_games")
