"""Cria a baseline completa do MVP.

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
        "automation_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "interval_seconds",
            sa.Integer(),
            server_default="120",
            nullable=False,
        ),
        sa.Column("last_enqueued_at", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "id = 1",
            name="ck_automation_settings_singleton",
        ),
        sa.CheckConstraint(
            "interval_seconds >= 1",
            name="ck_automation_settings_interval_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
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
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "process_charge",
                "process_due_charges",
                "retry_notification",
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
            ),
            server_default="queued",
            nullable=False,
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.String(length=120)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        sa.Column("deduplication_key", sa.String(length=255)),
        sa.Column(
            "retain_deduplication_key",
            sa.Boolean(),
            server_default="0",
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
        sa.CheckConstraint(
            "attempts >= 0",
            name="ck_processing_jobs_attempts",
        ),
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
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
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
    op.create_index("ix_users_email", "users", ["email"], unique=True)
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
        sa.CheckConstraint(
            "amount > 0",
            name="ck_charges_amount_positive",
        ),
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
    op.create_index("ix_charges_customer_id", "charges", ["customer_id"])
    op.create_index(
        "ix_charges_status_due_date",
        "charges",
        ["status", "due_date"],
    )
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("replaced_by_id", sa.Uuid()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"],
            ["refresh_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_refresh_sessions_user_expires",
        "refresh_sessions",
        ["user_id", "expires_at"],
    )
    op.create_index(
        "ix_refresh_sessions_user_id",
        "refresh_sessions",
        ["user_id"],
    )
    op.create_table(
        "notification_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("charge_id", sa.Uuid(), nullable=False),
        sa.Column("processing_job_id", sa.Uuid()),
        sa.Column(
            "notification_type",
            sa.Enum(
                "upcoming",
                "due_today",
                "overdue",
                name="notification_type",
                native_enum=False,
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
            ),
            nullable=False,
        ),
        sa.Column("destination", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "submission_status",
            sa.Enum(
                "pending",
                "succeeded",
                "failed",
                "unknown",
                "simulated",
                name="notification_submission_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("provider_message_id", sa.String(length=255)),
        sa.Column("submission_error_code", sa.Integer()),
        sa.Column("submission_error_title", sa.String(length=255)),
        sa.Column("submission_error_details", sa.Text()),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("policy_name", sa.String(length=120), nullable=False),
        sa.Column("decision_reason", sa.String(length=255), nullable=False),
        sa.Column("trace", sa.JSON()),
        sa.Column("provider_response", sa.JSON()),
        sa.Column(
            "delivery_status",
            sa.Enum(
                "not_started",
                "pending",
                "sent",
                "delivered",
                "read",
                "failed",
                name="notification_delivery_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="not_started",
            nullable=False,
        ),
        sa.Column("root_attempt_id", sa.Uuid()),
        sa.Column("retry_of_attempt_id", sa.Uuid()),
        sa.Column("retry_requested_by_user_id", sa.Uuid()),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("delivery_event_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_updated_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_error_code", sa.Integer()),
        sa.Column("delivery_error_title", sa.String(length=255)),
        sa.Column("delivery_error_details", sa.Text()),
        sa.Column("delivery_response", sa.JSON()),
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
        sa.ForeignKeyConstraint(
            ["processing_job_id"],
            ["processing_jobs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["retry_of_attempt_id"],
            ["notification_attempts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["retry_requested_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["root_attempt_id"],
            ["notification_attempts.id"],
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
    )
    op.create_index(
        "ix_notification_attempts_processed_at",
        "notification_attempts",
        ["processed_at"],
    )
    op.create_index(
        "ix_notification_attempts_processing_job_id",
        "notification_attempts",
        ["processing_job_id"],
    )
    op.create_index(
        "ix_notification_attempts_provider_message_id",
        "notification_attempts",
        ["provider_message_id"],
    )
    op.create_index(
        "ix_notification_attempts_retry_of_attempt_id",
        "notification_attempts",
        ["retry_of_attempt_id"],
    )
    op.create_index(
        "ix_notification_attempts_retry_requested_by_user_id",
        "notification_attempts",
        ["retry_requested_by_user_id"],
    )
    op.create_index(
        "ix_notification_attempts_root_attempt_id",
        "notification_attempts",
        ["root_attempt_id"],
    )


def downgrade() -> None:
    op.drop_table("notification_attempts")
    op.drop_table("refresh_sessions")
    op.drop_table("charges")
    op.drop_table("users")
    op.drop_table("processing_jobs")
    op.drop_table("customers")
    op.drop_table("automation_settings")
