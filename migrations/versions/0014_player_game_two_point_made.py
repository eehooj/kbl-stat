"""store visible player two-point makes

Revision ID: 0014_player_game_two_point_made
Revises: 0013_visible_player_game_stats
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0014_player_game_two_point_made"
down_revision = "0013_visible_player_game_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visible_player_game_stats", sa.Column("two_point_made", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("visible_player_game_stats", "two_point_made")
