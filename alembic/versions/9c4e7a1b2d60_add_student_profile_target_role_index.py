"""add index for student profile target roles

Revision ID: 9c4e7a1b2d60
Revises: f7a8b9c0d1e2
Create Date: 2026-11-12 09:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "9c4e7a1b2d60"
down_revision: str | Sequence[str] | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_student_profiles_target_role_id",
        "student_profiles",
        ["target_role_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_student_profiles_target_role_id",
        table_name="student_profiles",
    )
