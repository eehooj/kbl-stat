"""add visible Weekly 6 candidates

Revision ID: 0006_weekly6_visible_fixtures
Revises: 0005_team_form_snapshots
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0006_weekly6_visible_fixtures"
down_revision = "0005_team_form_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weekly6_visible_fixtures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("round_id", sa.Integer(), sa.ForeignKey("weekly6_rounds.id"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("venue", sa.String(length=150), nullable=False),
        sa.Column("first_team_name", sa.String(length=100), nullable=False),
        sa.Column("second_team_name", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("round_id", "ordinal", name="uq_weekly6_visible_round_ordinal"),
    )


def downgrade() -> None:
    op.drop_table("weekly6_visible_fixtures")
