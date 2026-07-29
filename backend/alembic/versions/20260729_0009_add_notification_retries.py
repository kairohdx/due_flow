"""Adiciona relacionamento auditável entre retentativas.

Revision ID: 20260729_0009
Revises: 20260729_0008
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0009"
down_revision: str | Sequence[str] | None = "20260729_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

old_job_type = sa.Enum(
    "process_charge",
    "process_due_charges",
    name="processing_job_type",
    native_enum=False,
    create_constraint=True,
)
new_job_type = sa.Enum(
    "process_charge",
    "process_due_charges",
    "retry_notification",
    name="processing_job_type",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.drop_constraint("processing_job_type", type_="check")
        batch_op.alter_column(
            "type",
            existing_type=old_job_type,
            type_=new_job_type,
            nullable=False,
        )
    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "root_attempt_id",
                sa.Uuid(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "retry_of_attempt_id",
                sa.Uuid(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "retry_requested_by_user_id",
                sa.Uuid(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "attempt_number",
                sa.Integer(),
                server_default="1",
                nullable=False,
            )
        )
        batch_op.create_foreign_key(
            "fk_notification_attempts_root_attempt_id",
            "notification_attempts",
            ["root_attempt_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_notification_attempts_retry_of_attempt_id",
            "notification_attempts",
            ["retry_of_attempt_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_notification_attempts_retry_requested_by_user_id",
            "users",
            ["retry_requested_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_notification_attempts_root_attempt_id",
            ["root_attempt_id"],
        )
        batch_op.create_index(
            "ix_notification_attempts_retry_of_attempt_id",
            ["retry_of_attempt_id"],
        )
        batch_op.create_index(
            "ix_notification_attempts_retry_requested_by_user_id",
            ["retry_requested_by_user_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.drop_index(
            "ix_notification_attempts_retry_requested_by_user_id"
        )
        batch_op.drop_index("ix_notification_attempts_retry_of_attempt_id")
        batch_op.drop_index("ix_notification_attempts_root_attempt_id")
        batch_op.drop_constraint(
            "fk_notification_attempts_retry_requested_by_user_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_notification_attempts_retry_of_attempt_id",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_notification_attempts_root_attempt_id",
            type_="foreignkey",
        )
        batch_op.drop_column("attempt_number")
        batch_op.drop_column("retry_requested_by_user_id")
        batch_op.drop_column("retry_of_attempt_id")
        batch_op.drop_column("root_attempt_id")
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.drop_constraint("processing_job_type", type_="check")
        batch_op.alter_column(
            "type",
            existing_type=new_job_type,
            type_=old_job_type,
            nullable=False,
        )
