"""constrain user roles to supported RBAC values

Revision ID: c1e49a7f2b30
Revises: b2a6d9e13f40
Create Date: 2026-11-09 09:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c1e49a7f2b30"
down_revision: str | Sequence[str] | None = "b2a6d9e13f40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_users_role", "users", "role IN ('student', 'admin')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
