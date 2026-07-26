"""create runtime snapshots table

Revision ID: 20260726_2300
Revises:
Create Date: 2026-07-26 23:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260726_2300"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_snapshots",
        sa.Column("snapshot_key", sa.String(length=128), primary_key=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )


def downgrade() -> None:
    op.drop_table("runtime_snapshots")
