"""link visible Weekly 6 candidates to visible schedule cards

Revision ID: 0007_weekly6_schedule_links
Revises: 0006_weekly6_visible_fixtures
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_weekly6_schedule_links"
down_revision = "0006_weekly6_visible_fixtures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weekly6_schedule_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("weekly6_fixture_id", sa.Integer(), sa.ForeignKey("weekly6_visible_fixtures.id"), nullable=False, unique=True),
        sa.Column("schedule_game_id", sa.Integer(), sa.ForeignKey("visible_schedule_games.id"), nullable=False, unique=True),
        sa.Column("matching_method", sa.String(length=100), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("weekly6_schedule_links")
