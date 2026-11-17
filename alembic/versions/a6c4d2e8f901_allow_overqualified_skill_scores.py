"""allow analysis skill levels above role requirements

Revision ID: a6c4d2e8f901
Revises: 91d2e7a4c6b8
Create Date: 2026-11-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a6c4d2e8f901"
down_revision: str | Sequence[str] | None = "91d2e7a4c6b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_skill_gaps") as batch_op:
        batch_op.drop_constraint("ck_analysis_skill_gap_levels", type_="check")
        batch_op.create_check_constraint(
            "ck_analysis_skill_gap_levels",
            "current_level >= 0 AND current_level <= 5 "
            "AND target_level >= 0 AND target_level <= 5",
        )


def downgrade() -> None:
    with op.batch_alter_table("analysis_skill_gaps") as batch_op:
        batch_op.drop_constraint("ck_analysis_skill_gap_levels", type_="check")
        batch_op.create_check_constraint(
            "ck_analysis_skill_gap_levels",
            "current_level >= 0 AND current_level <= 5 "
            "AND target_level >= 0 AND target_level <= 5 "
            "AND target_level >= current_level",
        )
