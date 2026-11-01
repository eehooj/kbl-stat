"""store scoring lead time derived from visible play-by-play

Revision ID: 0021_scoring_lead
Revises: 0020_good_defense
Create Date: 2026-11-01
"""
import sqlalchemy as sa
from alembic import op

revision = "0021_scoring_lead"
down_revision = "0020_good_defense"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visible_game_special_stats", sa.Column("scoring_lead_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("visible_game_special_stats", "scoring_lead_seconds")
