"""store visible play-by-play special scoring

Revision ID: 0017_special_scoring
Revises: 0016_player_game_dunks
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0017_special_scoring"
down_revision = "0016_player_game_dunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visible_game_special_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_game_id", sa.Integer(), sa.ForeignKey("visible_schedule_games.id"), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("bench_points", sa.Integer(), nullable=False),
        sa.Column("second_chance_points", sa.Integer(), nullable=False),
        sa.Column("calculation_version", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("schedule_game_id", "team_name", name="uq_visible_game_special_stat"),
    )


def downgrade() -> None:
    op.drop_table("visible_game_special_stats")
