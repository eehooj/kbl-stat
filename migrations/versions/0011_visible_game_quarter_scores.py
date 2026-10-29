"""store visible game quarter scores

Revision ID: 0011_visible_game_quarter_scores
Revises: 0010_visible_player_season_stats
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0011_visible_game_quarter_scores"
down_revision = "0010_visible_player_season_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visible_game_quarter_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_game_id", sa.Integer(), sa.ForeignKey("visible_schedule_games.id"), nullable=False, unique=True),
        sa.Column("record_url", sa.String(length=500), nullable=False, unique=True),
        sa.Column("first_team_name", sa.String(length=100), nullable=False),
        sa.Column("second_team_name", sa.String(length=100), nullable=False),
        sa.Column("first_quarters", sa.JSON(), nullable=False),
        sa.Column("second_quarters", sa.JSON(), nullable=False),
        sa.Column("first_total", sa.Integer(), nullable=False),
        sa.Column("second_total", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("visible_game_quarter_scores")
