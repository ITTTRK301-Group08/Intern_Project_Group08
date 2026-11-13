"""tạo bảng lộ trình học tập cá nhân hóa và nhiệm vụ theo tuần

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-13 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MYSQL_TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    """Tạo bảng lộ trình học tập và nhiệm vụ theo tuần."""
    op.create_table(
        "learning_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_learning_plan_status",
        ),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        **MYSQL_TABLE_ARGS,
    )
    op.create_index("ix_learning_plans_user_status", "learning_plans", ["user_id", "status"])
    op.create_index("ix_learning_plans_analysis", "learning_plans", ["analysis_id"])

    op.create_table(
        "learning_plan_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("task_description", sa.Text(), nullable=False),
        sa.Column("estimated_hours", sa.Float(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "week_number >= 1 AND week_number <= 8",
            name="ck_learning_plan_item_week",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["learning_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resource_id"], ["learning_resources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        **MYSQL_TABLE_ARGS,
    )
    op.create_index("ix_learning_plan_items_plan_week", "learning_plan_items", ["plan_id", "week_number"])


def downgrade() -> None:
    """Xóa bảng nhiệm vụ và bảng lộ trình học tập."""
    op.drop_index("ix_learning_plan_items_plan_week", table_name="learning_plan_items")
    op.drop_table("learning_plan_items")
    op.drop_index("ix_learning_plans_analysis", table_name="learning_plans")
    op.drop_index("ix_learning_plans_user_status", table_name="learning_plans")
    op.drop_table("learning_plans")
