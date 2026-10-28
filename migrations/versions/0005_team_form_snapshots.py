"""add leakage-safe team form snapshots

Revision ID: 0005_team_form_snapshots
Revises: 0004_team_season_standings
Create Date: 2026-10-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_team_form_snapshots"
down_revision = "0004_team_season_standings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_form_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season_id", sa.Integer(), sa.ForeignKey("seasons.id"), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("games_played", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("recent_five_wins", sa.Integer(), nullable=False),
        sa.Column("recent_five_losses", sa.Integer(), nullable=False),
        sa.Column("recent_ten_wins", sa.Integer(), nullable=False),
        sa.Column("recent_ten_losses", sa.Integer(), nullable=False),
        sa.Column("average_points_for", sa.Float(), nullable=False),
        sa.Column("average_points_against", sa.Float(), nullable=False),
        sa.Column("rest_days", sa.Integer(), nullable=True),
        sa.Column("calculation_version", sa.String(length=50), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("season_id", "team_name", "as_of", name="uq_team_form_snapshot"),
    )


def downgrade() -> None:
    op.drop_table("team_form_snapshots")
