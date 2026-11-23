"""repair analysis status check constraint

Some databases were stamped at the latest Alembic revision while the
`ck_analysis_status` constraint still had the legacy ``running`` value.
The analysis pipeline writes ``processing``, which the stale check rejects
with MySQL error 3819. This migration makes the database constraint match
the model and the original d3f4a8c21b60 migration.

Revision ID: b4e7c1d9a2f3
Revises: a9b8c7d6e5f4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4e7c1d9a2f3"
down_revision: str | Sequence[str] | None = "a9b8c7d6e5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE analyses DROP CHECK ck_analysis_status"))
    op.execute(
        sa.text("UPDATE analyses SET status = 'processing' WHERE status = 'running'")
    )
    op.execute(
        sa.text(
            "ALTER TABLE analyses ADD CONSTRAINT ck_analysis_status "
            "CHECK (status IN ('pending', 'processing', 'completed', 'failed'))"
        )
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE analyses DROP CHECK ck_analysis_status"))
    op.execute(
        sa.text("UPDATE analyses SET status = 'running' WHERE status = 'processing'")
    )
    op.execute(
        sa.text(
            "ALTER TABLE analyses ADD CONSTRAINT ck_analysis_status "
            "CHECK (status IN ('pending', 'running', 'completed', 'failed'))"
        )
    )
