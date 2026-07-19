"""Create normalized completed activity storage.

Revision ID: 20260719_0001
Revises:
Create Date: 2026-07-19
"""

import sqlalchemy as sa
from alembic import op

revision = "20260719_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "completed_activities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("athlete_id", sa.String(length=128), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("import_status", sa.String(length=16), nullable=False),
        sa.Column("source_format", sa.String(length=8), nullable=False),
        sa.Column("parser_name", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("distance_meters", sa.Float(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("samples", sa.JSON(), nullable=False),
        sa.Column("laps", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id", "checksum", name="uq_activity_athlete_checksum"),
    )
    op.create_index("ix_completed_activities_athlete_id", "completed_activities", ["athlete_id"])


def downgrade() -> None:
    op.drop_index("ix_completed_activities_athlete_id", table_name="completed_activities")
    op.drop_table("completed_activities")
