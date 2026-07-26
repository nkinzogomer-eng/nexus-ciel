"""phase 2 persistence baseline

Revision ID: 202607270300
Revises:
Create Date: 2026-07-27 03:00:00+09:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202607270300"
down_revision = None
branch_labels = None
depends_on = None



def upgrade() -> None:
    op.create_table(
        "mission_states",
        sa.Column("mission_id", sa.String(length=36), primary_key=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resumable_after_crash", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "mission_reports",
        sa.Column("mission_id", sa.String(length=36), primary_key=True),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("duration_s", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("validation", sa.JSON(), nullable=False),
        sa.Column("learned", sa.JSON(), nullable=False),
        sa.Column("guard_events", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "mission_journal",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("precedent_hash", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mission_journal_mission_id", "mission_journal", ["mission_id"])
    op.create_table(
        "capabilities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("stats", sa.JSON(), nullable=False),
    )
    op.create_table(
        "routing_telemetry",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("mission_id", sa.String(length=36), nullable=True),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cost_avoided_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_routing_telemetry_mission_id", "routing_telemetry", ["mission_id"])



def downgrade() -> None:
    op.drop_index("ix_routing_telemetry_mission_id", table_name="routing_telemetry")
    op.drop_table("routing_telemetry")
    op.drop_table("capabilities")
    op.drop_index("ix_mission_journal_mission_id", table_name="mission_journal")
    op.drop_table("mission_journal")
    op.drop_table("mission_reports")
    op.drop_table("mission_states")
