"""Cria a fila de jobs de processamento.

Revision ID: 20260729_0002
Revises: 20260729_0001
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0002"
down_revision: str | Sequence[str] | None = "20260729_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "process_charge",
                "process_due_charges",
                name="processing_job_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "processing",
                "completed",
                "failed",
                name="processing_job_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("deduplication_key", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_processing_jobs_attempts"),
        sa.CheckConstraint(
            "max_attempts >= 1",
            name="ck_processing_jobs_max_attempts",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deduplication_key",
            name="uq_processing_jobs_deduplication_key",
        ),
    )
    op.create_index(
        "ix_processing_jobs_available",
        "processing_jobs",
        ["status", "scheduled_for", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_processing_jobs_available",
        table_name="processing_jobs",
    )
    op.drop_table("processing_jobs")

