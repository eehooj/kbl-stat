"""store visible play-by-play good-defense counts

Revision ID: 0020_good_defense
Revises: 0019_game_shooting
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0020_good_defense"
down_revision = "0019_game_shooting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visible_game_special_stats", sa.Column("good_defense", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("visible_game_special_stats", "good_defense")
