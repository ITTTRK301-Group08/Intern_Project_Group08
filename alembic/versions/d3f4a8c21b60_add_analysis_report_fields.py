"""add analysis report fields and processing status

Revision ID: d3f4a8c21b60
Revises: c1e49a7f2b30
Create Date: 2026-11-12 08:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3f4a8c21b60"
down_revision: str | Sequence[str] | None = "c1e49a7f2b30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_constraint("ck_analysis_status", type_="check")

    op.execute(
        sa.text("UPDATE analyses SET status = 'processing' WHERE status = 'running'")
    )

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.add_column(sa.Column("readiness_score", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_analysis_readiness_score",
            "readiness_score IS NULL OR (readiness_score >= 0 AND readiness_score <= 100)",
        )
        batch_op.create_check_constraint(
            "ck_analysis_status",
            "status IN ('pending', 'processing', 'completed', 'failed')",
        )

    with op.batch_alter_table("analysis_skill_gaps") as batch_op:
        batch_op.add_column(sa.Column("evidence", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "has_evidence",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )
    op.execute(
        sa.text(
            "UPDATE analysis_skill_gaps SET current_level = 0 "
            "WHERE has_evidence = 0"
        )
    )
    with op.batch_alter_table("analysis_skill_gaps") as batch_op:
        batch_op.create_check_constraint(
            "ck_analysis_skill_gap_evidence",
            "(has_evidence = 1 AND evidence IS NOT NULL "
            "AND length(trim(evidence)) > 0) "
            "OR (has_evidence = 0 AND current_level = 0)",
        )


def downgrade() -> None:
    with op.batch_alter_table("analysis_skill_gaps") as batch_op:
        batch_op.drop_constraint("ck_analysis_skill_gap_evidence", type_="check")
        batch_op.drop_column("has_evidence")
        batch_op.drop_column("evidence")

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_constraint("ck_analysis_readiness_score", type_="check")
        batch_op.drop_constraint("ck_analysis_status", type_="check")

    op.execute(
        sa.text("UPDATE analyses SET status = 'running' WHERE status = 'processing'")
    )

    with op.batch_alter_table("analyses") as batch_op:
        batch_op.drop_column("readiness_score")
        batch_op.create_check_constraint(
            "ck_analysis_status",
            "status IN ('pending', 'running', 'completed', 'failed')",
        )
