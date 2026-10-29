"""store date-specific verified player availability

Revision ID: 0012_player_availability
Revises: 0011_visible_game_quarter_scores
Create Date: 2026-10-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0012_player_availability"
down_revision = "0011_visible_game_quarter_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_availability",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_name", sa.String(length=100), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=True),
        sa.Column("availability_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("player_name", "team_name", "availability_date", name="uq_player_availability_day"),
    )


def downgrade() -> None:
    op.drop_table("player_availability")
