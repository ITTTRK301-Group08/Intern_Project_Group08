"""add active status to skills

Revision ID: c5e9b22d7a01
Revises: 4f2fe7519541
Create Date: 2026-11-19 23:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5e9b22d7a01"
down_revision: str | Sequence[str] | None = "4f2fe7519541"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "skills",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )


def downgrade() -> None:
    op.drop_column("skills", "is_active")
