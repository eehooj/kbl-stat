"""store visible player game box scores

Revision ID: 0013_visible_player_game_stats
Revises: 0012_player_availability
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0013_visible_player_game_stats"
down_revision = "0012_player_availability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visible_player_game_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("schedule_game_id", sa.Integer(), sa.ForeignKey("visible_schedule_games.id"), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("player_name", sa.String(length=100), nullable=False),
        sa.Column("minutes", sa.String(length=10), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("rebounds", sa.Integer(), nullable=False),
        sa.Column("assists", sa.Integer(), nullable=False),
        sa.Column("steals", sa.Integer(), nullable=False),
        sa.Column("blocks", sa.Integer(), nullable=False),
        sa.Column("turnovers", sa.Integer(), nullable=False),
        sa.Column("fouls", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("schedule_game_id", "team_name", "player_name", name="uq_visible_player_game_stat"),
    )


def downgrade() -> None:
    op.drop_table("visible_player_game_stats")
