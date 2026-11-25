"""reconcile skill-gap evidence fields for legacy databases

Revision ID: c8f19a2d4e60
Revises: a6d3f0c2b841
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c8f19a2d4e60"
down_revision: str | Sequence[str] | None = "a6d3f0c2b841"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {
        column["name"] for column in inspector.get_columns("analysis_skill_gaps")
    }

    if "evidence" not in column_names:
        with op.batch_alter_table("analysis_skill_gaps") as batch_op:
            batch_op.add_column(sa.Column("evidence", sa.Text(), nullable=True))

    if "has_evidence" not in column_names:
        with op.batch_alter_table("analysis_skill_gaps") as batch_op:
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

    constraint_names = {
        constraint.get("name")
        for constraint in sa.inspect(bind).get_check_constraints(
            "analysis_skill_gaps"
        )
    }
    if "ck_analysis_skill_gap_evidence" not in constraint_names:
        with op.batch_alter_table("analysis_skill_gaps") as batch_op:
            batch_op.create_check_constraint(
                "ck_analysis_skill_gap_evidence",
                "(has_evidence = 1 AND evidence IS NOT NULL "
                "AND length(trim(evidence)) > 0) "
                "OR (has_evidence = 0 AND current_level = 0)",
            )


def downgrade() -> None:
    """Leave shared fields in place; the base analysis migration owns them."""
