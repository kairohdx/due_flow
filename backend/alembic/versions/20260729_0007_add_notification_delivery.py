"""Adiciona o estado assíncrono de entrega das mensagens.

Revision ID: 20260729_0007
Revises: 20260729_0006
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0007"
down_revision: str | Sequence[str] | None = "20260729_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "delivery_status",
                sa.Enum(
                    "pending",
                    "sent",
                    "delivered",
                    "read",
                    "failed",
                    name="notification_delivery_status",
                    native_enum=False,
                    create_constraint=True,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("delivery_event_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("delivery_updated_at", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("delivery_error_code", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("delivery_error_title", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("delivery_error_details", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("delivery_response", sa.JSON(), nullable=True)
        )
        batch_op.create_index(
            "ix_notification_attempts_provider_message_id",
            ["provider_message_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_attempts") as batch_op:
        batch_op.drop_index("ix_notification_attempts_provider_message_id")
        batch_op.drop_constraint(
            "notification_delivery_status",
            type_="check",
        )
        batch_op.drop_column("delivery_response")
        batch_op.drop_column("delivery_error_details")
        batch_op.drop_column("delivery_error_title")
        batch_op.drop_column("delivery_error_code")
        batch_op.drop_column("delivery_updated_at")
        batch_op.drop_column("delivery_event_at")
        batch_op.drop_column("delivery_status")
