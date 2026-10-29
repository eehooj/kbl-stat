"""store visible player field-goal makes and attempts

Revision ID: 0015_player_game_field_goals
Revises: 0014_player_game_two_point_made
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0015_player_game_field_goals"
down_revision = "0014_player_game_two_point_made"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visible_player_game_stats", sa.Column("field_goals_made", sa.Integer(), nullable=True))
    op.add_column("visible_player_game_stats", sa.Column("field_goals_attempted", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("visible_player_game_stats", "field_goals_attempted")
    op.drop_column("visible_player_game_stats", "field_goals_made")
