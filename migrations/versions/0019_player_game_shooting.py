"""store visible player three-point and free-throw fields

Revision ID: 0019_game_shooting
Revises: 0018_roster_snapshot
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0019_game_shooting"
down_revision = "0018_roster_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visible_player_game_stats", sa.Column("three_point_made", sa.Integer(), nullable=True))
    op.add_column("visible_player_game_stats", sa.Column("three_point_attempted", sa.Integer(), nullable=True))
    op.add_column("visible_player_game_stats", sa.Column("free_throw_made", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("visible_player_game_stats", "free_throw_made")
    op.drop_column("visible_player_game_stats", "three_point_attempted")
    op.drop_column("visible_player_game_stats", "three_point_made")
