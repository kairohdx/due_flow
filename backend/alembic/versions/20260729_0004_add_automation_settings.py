"""Adiciona controle persistido da automação.

Revision ID: 20260729_0004
Revises: 20260729_0003
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0004"
down_revision: str | Sequence[str] | None = "20260729_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "retain_deduplication_key",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )

    op.create_table(
        "automation_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "interval_seconds",
            sa.Integer(),
            server_default="120",
            nullable=False,
        ),
        sa.Column("last_enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
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
    op.execute(
        sa.text(
            "INSERT INTO automation_settings "
            "(id, enabled, interval_seconds) VALUES (1, false, 120)"
        )
    )


def downgrade() -> None:
    op.drop_table("automation_settings")
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.drop_column("retain_deduplication_key")

