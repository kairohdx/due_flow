"""Vincula tentativas de notificação às execuções.

Revision ID: 20260729_0006
Revises: 20260729_0005
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0006"
down_revision: str | Sequence[str] | None = "20260729_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.add_column(
            sa.Column("processing_job_id", sa.Uuid(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_notification_attempts_processing_job_id",
            "processing_jobs",
            ["processing_job_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_notification_attempts_processing_job_id",
            ["processing_job_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.drop_index("ix_notification_attempts_processing_job_id")
        batch_op.drop_constraint(
            "fk_notification_attempts_processing_job_id",
            type_="foreignkey",
        )
        batch_op.drop_column("processing_job_id")
