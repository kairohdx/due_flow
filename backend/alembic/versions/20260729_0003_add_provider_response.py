"""Adiciona resposta segura do provider à tentativa.

Revision ID: 20260729_0003
Revises: 20260729_0002
Create Date: 2026-07-29
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0003"
down_revision: str | Sequence[str] | None = "20260729_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_attempts",
        sa.Column("provider_response", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notification_attempts", "provider_response")

