"""store visible player season totals

Revision ID: 0010_visible_player_season_stats
Revises: 0009_stats_king_visible_games
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_visible_player_season_stats"
down_revision = "0009_stats_king_visible_games"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visible_player_season_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("player_name", sa.String(length=100), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("games_played", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("rebounds", sa.Integer(), nullable=False),
        sa.Column("assists", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("season_id", "player_name", "team_name", name="uq_visible_player_season_stat"),
    )


def downgrade() -> None:
    op.drop_table("visible_player_season_stats")
