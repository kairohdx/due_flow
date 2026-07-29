"""Cria as tabelas iniciais.

Revision ID: 20260729_0001
Revises:
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_phone", "customers", ["phone"], unique=False)

    op.create_table(
        "charges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "paid",
                "canceled",
                name="charge_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "reminder_days_before",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),
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
        sa.CheckConstraint("amount > 0", name="ck_charges_amount_positive"),
        sa.CheckConstraint(
            "reminder_days_before >= 0",
            name="ck_charges_reminder_days_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_charges_customer_id",
        "charges",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_charges_status_due_date",
        "charges",
        ["status", "due_date"],
        unique=False,
    )

    op.create_table(
        "notification_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("charge_id", sa.Uuid(), nullable=False),
        sa.Column(
            "notification_type",
            sa.Enum(
                "upcoming",
                "due_today",
                "overdue",
                name="notification_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.Enum(
                "fake",
                "meta",
                name="notification_provider",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("destination", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "sent",
                "failed",
                "simulated",
                name="notification_attempt_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("policy_name", sa.String(length=120), nullable=False),
        sa.Column("decision_reason", sa.String(length=255), nullable=False),
        sa.Column("trace", sa.JSON(), nullable=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["charge_id"],
            ["charges.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_notification_attempts_idempotency_key",
        ),
    )
    op.create_index(
        "ix_notification_attempts_charge_id",
        "notification_attempts",
        ["charge_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_attempts_processed_at",
        "notification_attempts",
        ["processed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_attempts_processed_at",
        table_name="notification_attempts",
    )
    op.drop_index(
        "ix_notification_attempts_charge_id",
        table_name="notification_attempts",
    )
    op.drop_table("notification_attempts")
    op.drop_index("ix_charges_status_due_date", table_name="charges")
    op.drop_index("ix_charges_customer_id", table_name="charges")
    op.drop_table("charges")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_table("customers")

