"""link Daily Picks questions to visible schedule cards

Revision ID: 0008_daily_picks_schedule_links
Revises: 0007_weekly6_schedule_links
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_daily_picks_schedule_links"
down_revision = "0007_weekly6_schedule_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_picks_schedule_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("challenge_questions.id"), nullable=False, unique=True),
        sa.Column("schedule_game_id", sa.Integer(), sa.ForeignKey("visible_schedule_games.id"), nullable=False),
        sa.Column("matching_method", sa.String(length=100), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("daily_picks_schedule_links")
