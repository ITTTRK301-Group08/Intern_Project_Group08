"""auto-abandon inactive interview sessions

Revision ID: a9b8c7d6e5f4
Revises: 4f2fe7519541, e71b3c9d4a20
Create Date: 2026-11-18 01:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9b8c7d6e5f4"
down_revision: str | Sequence[str] | None = ("4f2fe7519541", "e71b3c9d4a20")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.drop_constraint("ck_interview_sessions_status", type_="check")
        batch_op.create_check_constraint(
            "ck_interview_sessions_status",
            "status IN ('ready', 'in_progress', 'completed', 'failed', 'abandoned')",
        )
        batch_op.create_index(
            "ix_interview_sessions_user_status_updated",
            ["user_id", "status", "updated_at"],
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE interview_sessions SET status = 'failed' "
            "WHERE status = 'abandoned'"
        )
    )
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.drop_index("ix_interview_sessions_user_status_updated")
        batch_op.drop_constraint("ck_interview_sessions_status", type_="check")
        batch_op.create_check_constraint(
            "ck_interview_sessions_status",
            "status IN ('ready', 'in_progress', 'completed', 'failed')",
        )
