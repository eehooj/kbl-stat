"""store visible player dunk makes

Revision ID: 0016_player_game_dunks
Revises: 0015_player_game_field_goals
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0016_player_game_dunks"
down_revision = "0015_player_game_field_goals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visible_player_game_stats", sa.Column("dunk_made", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("visible_player_game_stats", "dunk_made")
