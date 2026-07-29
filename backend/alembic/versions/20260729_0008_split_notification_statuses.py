"""Separa o resultado do envio do estado de entrega.

Revision ID: 20260729_0008
Revises: 20260729_0007
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0008"
down_revision: str | Sequence[str] | None = "20260729_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

old_delivery = sa.Enum(
    "pending",
    "sent",
    "delivered",
    "read",
    "failed",
    name="notification_delivery_status",
    native_enum=False,
    create_constraint=True,
)
new_delivery = sa.Enum(
    "not_started",
    "pending",
    "sent",
    "delivered",
    "read",
    "failed",
    name="notification_delivery_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.drop_constraint(
            "notification_attempt_status",
            type_="check",
        )
        batch_op.drop_constraint(
            "notification_delivery_status",
            type_="check",
        )
        batch_op.alter_column(
            "status",
            new_column_name="submission_status",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            "error",
            new_column_name="submission_error_details",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column("submission_error_code", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "submission_error_title",
                sa.String(length=255),
                nullable=True,
            )
        )
        batch_op.alter_column(
            "delivery_status",
            existing_type=old_delivery,
            type_=new_delivery,
            nullable=True,
        )
        batch_op.create_check_constraint(
            "notification_submission_status",
            "submission_status IN "
            "('pending', 'succeeded', 'failed', 'unknown', 'simulated')",
        )

    op.execute(
        "UPDATE notification_attempts "
        "SET submission_status = 'succeeded' "
        "WHERE submission_status = 'sent'"
    )
    op.execute(
        "UPDATE notification_attempts "
        "SET delivery_status = 'not_started' "
        "WHERE delivery_status IS NULL"
    )

    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.alter_column(
            "delivery_status",
            existing_type=new_delivery,
            nullable=False,
            server_default="not_started",
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.alter_column(
            "delivery_status",
            existing_type=new_delivery,
            nullable=True,
            server_default=None,
        )

    op.execute(
        "UPDATE notification_attempts "
        "SET delivery_status = NULL "
        "WHERE delivery_status = 'not_started'"
    )
    op.execute(
        "UPDATE notification_attempts "
        "SET submission_status = 'sent' "
        "WHERE submission_status = 'succeeded'"
    )
    op.execute(
        "UPDATE notification_attempts "
        "SET submission_status = 'failed' "
        "WHERE submission_status = 'unknown'"
    )

    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.drop_constraint(
            "notification_submission_status",
            type_="check",
        )
        batch_op.drop_constraint(
            "notification_delivery_status",
            type_="check",
        )
        batch_op.alter_column(
            "delivery_status",
            existing_type=new_delivery,
            type_=old_delivery,
            nullable=True,
        )
        batch_op.drop_column("submission_error_title")
        batch_op.drop_column("submission_error_code")
        batch_op.alter_column(
            "submission_error_details",
            new_column_name="error",
            existing_type=sa.Text(),
            nullable=True,
        )
        batch_op.alter_column(
            "submission_status",
            new_column_name="status",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "notification_attempt_status",
            "status IN ('pending', 'sent', 'failed', 'simulated')",
        )
