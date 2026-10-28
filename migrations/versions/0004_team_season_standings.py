"""add visible team standings

Revision ID: 0004_team_season_standings
Revises: 0003_visible_schedule_games
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_team_season_standings"
down_revision = "0003_visible_schedule_games"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_season_standings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=False),
        sa.Column("games_back", sa.Float(), nullable=False),
        sa.Column("recent_five", sa.String(length=20), nullable=False),
        sa.Column("streak", sa.String(length=20), nullable=False),
        sa.Column("home_record", sa.String(length=20), nullable=False),
        sa.Column("away_record", sa.String(length=20), nullable=False),
        sa.Column("next_opponent_name", sa.String(length=100), nullable=True),
        sa.Column("head_to_head", sa.String(length=30), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("season_id", "team_name", name="uq_team_season_standing"),
    )


def downgrade() -> None:
    op.drop_table("team_season_standings")
