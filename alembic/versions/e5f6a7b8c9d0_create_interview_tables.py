"""tạo bảng phiên phỏng vấn thử và câu hỏi phỏng vấn

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-10 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Cấu hình bảng thống nhất với các migration hiện có của dự án.
MYSQL_TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    """Tạo bảng phiên phỏng vấn và bảng câu hỏi phỏng vấn."""
    op.create_table(
        "interview_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("career_role_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="ready",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["career_role_id"],
            ["career_roles.id"],
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'in_progress', 'completed', 'failed')",
            name="ck_interview_sessions_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        **MYSQL_TABLE_ARGS,
    )
    op.create_index(
        "ix_interview_sessions_user_created",
        "interview_sessions",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_interview_sessions_career_role_id",
        "interview_sessions",
        ["career_role_id"],
    )

    op.create_table(
        "interview_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("competency", sa.String(length=255), nullable=False),
        sa.Column("evaluation_criteria", sa.JSON(), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["interview_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "question_order",
            name="uq_interview_question_order",
        ),
        sa.CheckConstraint(
            "question_order >= 1 AND question_order <= 3",
            name="ck_interview_questions_order",
        ),
        **MYSQL_TABLE_ARGS,
    )


def downgrade() -> None:
    """Xóa bảng câu hỏi và bảng phiên phỏng vấn theo thứ tự an toàn."""
    op.drop_table("interview_questions")
    op.drop_index(
        "ix_interview_sessions_career_role_id",
        table_name="interview_sessions",
    )
    op.drop_index(
        "ix_interview_sessions_user_created",
        table_name="interview_sessions",
    )
    op.drop_table("interview_sessions")
