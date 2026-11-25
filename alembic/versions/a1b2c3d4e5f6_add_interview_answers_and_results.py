"""thêm bảng câu trả lời phỏng vấn và kết quả điểm của phiên

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-11-15 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MYSQL_TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}

OLD_SESSION_STATUS_CHECK = "status IN ('ready', 'in_progress', 'completed', 'failed')"
NEW_SESSION_STATUS_CHECK = (
    "status IN ('ready', 'in_progress', 'completed', 'abandoned', 'failed')"
)


def upgrade() -> None:
    """Bổ sung cột kết quả phiên và bảng câu trả lời có điểm/feedback."""
    op.drop_constraint(
        "ck_interview_sessions_status",
        "interview_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_interview_sessions_status",
        "interview_sessions",
        NEW_SESSION_STATUS_CHECK,
    )
    op.add_column(
        "interview_sessions",
        sa.Column("total_score", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        "interview_sessions",
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "interview_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["interview_questions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", name="uq_interview_answers_question"),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_interview_answers_score",
        ),
        **MYSQL_TABLE_ARGS,
    )


def downgrade() -> None:
    """Gỡ bảng câu trả lời và các cột kết quả phiên."""
    op.drop_table("interview_answers")

    # Trạng thái abandoned không tồn tại trong phiên bản cũ của check constraint.
    op.execute(
        sa.text(
            "UPDATE interview_sessions SET status = 'failed' "
            "WHERE status = 'abandoned'"
        )
    )
    op.drop_constraint(
        "ck_interview_sessions_status",
        "interview_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_interview_sessions_status",
        "interview_sessions",
        OLD_SESSION_STATUS_CHECK,
    )
    op.drop_column("interview_sessions", "completed_at")
    op.drop_column("interview_sessions", "total_score")
