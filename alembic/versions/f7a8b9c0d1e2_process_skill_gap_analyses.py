"""process skill-gap analyses and persist readiness results

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-11-12 08:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column(
            "source_type",
            sa.String(length=20),
            nullable=False,
            server_default="profile",
        ),
    )
    op.add_column(
        "analyses", sa.Column("readiness_score", sa.Integer(), nullable=True)
    )
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.create_check_constraint(
            "ck_analysis_source_type",
            "source_type IN ('profile', 'cv', 'cv_and_profile')",
        )
        batch_op.create_check_constraint(
            "ck_analysis_readiness_score",
            "readiness_score IS NULL OR "
            "(readiness_score >= 0 AND readiness_score <= 100)",
        )
    op.execute(
        "UPDATE analyses SET source_type = "
        "CASE WHEN cv_id IS NULL THEN 'profile' ELSE 'cv' END"
    )

    op.add_column(
        "analysis_skill_gaps",
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "analysis_skill_gaps",
        sa.Column(
            "weight",
            sa.Float(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "analysis_skill_gaps", sa.Column("gap", sa.Integer(), nullable=True)
    )
    op.execute(
        "UPDATE analysis_skill_gaps "
        "SET gap = CASE WHEN target_level > current_level "
        "THEN target_level - current_level ELSE 0 END"
    )
    op.alter_column(
        "analysis_skill_gaps",
        "gap",
        existing_type=sa.Integer(),
        nullable=False,
    )
    with op.batch_alter_table("analysis_skill_gaps") as batch_op:
        batch_op.drop_constraint("ck_analysis_skill_gap_levels", type_="check")
        batch_op.create_check_constraint(
            "ck_analysis_skill_gap_levels",
            "current_level >= 0 AND current_level <= 5 "
            "AND target_level >= 0 AND target_level <= 5",
        )
        batch_op.create_check_constraint(
            "ck_analysis_skill_gap_value",
            "(target_level >= current_level AND gap = target_level - current_level) "
            "OR (target_level < current_level AND gap = 0)",
        )
        batch_op.create_check_constraint(
            "ck_analysis_skill_gap_weight", "weight > 0"
        )


def downgrade() -> None:
    with op.batch_alter_table("analysis_skill_gaps") as batch_op:
        batch_op.drop_constraint("ck_analysis_skill_gap_weight", type_="check")
        batch_op.drop_constraint("ck_analysis_skill_gap_value", type_="check")
        batch_op.drop_constraint("ck_analysis_skill_gap_levels", type_="check")
        batch_op.create_check_constraint(
            "ck_analysis_skill_gap_levels",
            "current_level >= 0 AND current_level <= 5 "
            "AND target_level >= 0 AND target_level <= 5 "
            "AND target_level >= current_level",
        )
        batch_op.drop_column("gap")
        batch_op.drop_column("weight")
        batch_op.drop_column("is_required")

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_constraint("ck_analysis_readiness_score", type_="check")
        batch_op.drop_constraint("ck_analysis_source_type", type_="check")
        batch_op.drop_column("readiness_score")
        batch_op.drop_column("source_type")
