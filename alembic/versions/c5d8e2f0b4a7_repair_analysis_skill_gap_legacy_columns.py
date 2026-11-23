"""repair legacy columns on analysis_skill_gaps

Legacy local databases still contain ``gap``, ``is_required`` and ``weight``
columns on ``analysis_skill_gaps``. The current model computes the gap from
``target_level - current_level`` and does not map those columns, so MySQL
rejects inserts with error 1364 ("Field 'gap' doesn't have a default value").
This migration removes the stale columns and their check constraints.

Revision ID: c5d8e2f0b4a7
Revises: b4e7c1d9a2f3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d8e2f0b4a7"
down_revision: str | Sequence[str] | None = "b4e7c1d9a2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "analysis_skill_gaps"


def _constraint_names() -> set[str]:
    return {
        item.get("name")
        for item in sa.inspect(op.get_bind()).get_check_constraints(TABLE)
    }


def _column_names() -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(TABLE)}


def upgrade() -> None:
    constraints = _constraint_names()
    if "ck_analysis_skill_gap_value" in constraints:
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE} DROP CHECK ck_analysis_skill_gap_value"
            )
        )
    if "ck_analysis_skill_gap_weight" in constraints:
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE} DROP CHECK ck_analysis_skill_gap_weight"
            )
        )

    columns = _column_names()
    for name in ("gap", "is_required", "weight"):
        if name in columns:
            op.execute(sa.text(f"ALTER TABLE {TABLE} DROP COLUMN {name}"))


def downgrade() -> None:
    columns = _column_names()
    if "gap" not in columns:
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE} ADD COLUMN gap INT NOT NULL DEFAULT 0 "
                "AFTER target_level"
            )
        )
    if "is_required" not in columns:
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE} ADD COLUMN is_required BOOLEAN NOT NULL "
                "DEFAULT 1 AFTER recommendation"
            )
        )
    if "weight" not in columns:
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE} ADD COLUMN weight FLOAT NOT NULL "
                "DEFAULT 1 AFTER is_required"
            )
        )

    constraints = _constraint_names()
    if "ck_analysis_skill_gap_value" not in constraints:
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE} ADD CONSTRAINT ck_analysis_skill_gap_value "
                "CHECK ((target_level >= current_level AND gap = target_level - current_level) "
                "OR (target_level < current_level AND gap = 0))"
            )
        )
    if "ck_analysis_skill_gap_weight" not in constraints:
        op.execute(
            sa.text(
                f"ALTER TABLE {TABLE} ADD CONSTRAINT ck_analysis_skill_gap_weight "
                "CHECK (weight > 0)"
            )
        )
