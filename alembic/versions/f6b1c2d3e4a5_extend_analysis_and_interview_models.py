"""mở rộng mô hình phân tích kỹ năng và phiên phỏng vấn

Bổ sung các cột còn thiếu cho M4/M6, tạo bảng câu trả lời phỏng vấn và
cập nhật ràng buộc trạng thái. Toàn bộ bước backfill dữ liệu cũ được thực
hiện trước khi siết ràng buộc để không phá hỏng dữ liệu hiện có.

Revision ID: f6b1c2d3e4a5
Revises: e5f6a7b8c9d0
Create Date: 2026-11-12 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6b1c2d3e4a5"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MYSQL_TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}

ANALYSIS_STATUS_CHECK = "status IN ('pending', 'processing', 'completed', 'failed')"
ANALYSIS_READINESS_CHECK = (
    "readiness_score IS NULL OR "
    "(readiness_score >= 0 AND readiness_score <= 100)"
)
SKILL_LEVELS_CHECK = (
    "current_level >= 0 AND current_level <= 5 "
    "AND required_level >= 0 AND required_level <= 5"
)
SKILL_GAP_SCORE_CHECK = "gap_score >= 0 AND gap_score <= 5"
INTERVIEW_STATUS_CHECK = "status IN ('in_progress', 'completed', 'abandoned')"
INTERVIEW_TOTAL_SCORE_CHECK = (
    "total_score IS NULL OR (total_score >= 0 AND total_score <= 100)"
)

# Trạng thái cũ hợp lệ trước khi đổi quy ước trạng thái của M4/M6.
OLD_ANALYSIS_STATUS_CHECK = "status IN ('pending', 'running', 'completed', 'failed')"
OLD_INTERVIEW_STATUS_CHECK = (
    "status IN ('ready', 'in_progress', 'completed', 'failed')"
)
OLD_SKILL_LEVELS_CHECK = (
    "current_level >= 0 AND current_level <= 5 "
    "AND target_level >= 0 AND target_level <= 5 "
    "AND target_level >= current_level"
)


def _is_mysql() -> bool:
    """Cho biết migration đang chạy trên MySQL hay không."""
    return op.get_bind().dialect.name == "mysql"


def _drop_check(table_name: str, constraint_name: str) -> None:
    """Xóa check constraint theo cách phù hợp với từng dialect."""
    if _is_mysql():
        op.drop_constraint(constraint_name, table_name, type_="check")
    else:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(constraint_name, type_="check")


def _create_check(
    table_name: str, constraint_name: str, condition: str
) -> None:
    """Tạo check constraint theo cách phù hợp với từng dialect."""
    if _is_mysql():
        op.create_check_constraint(constraint_name, table_name, condition)
    else:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_check_constraint(constraint_name, condition)


def upgrade() -> None:
    """Bổ sung cột/bảng mới và cập nhật ràng buộc trạng thái."""
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # Bảng analyses (M4): thêm điểm sẵn sàng, nguồn benchmark, lý do lỗi.
    # ------------------------------------------------------------------
    op.add_column(
        "analyses",
        sa.Column("readiness_score", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("market_source", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("benchmark_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "analyses",
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
    )

    analyses_table = sa.table(
        "analyses",
        sa.column("status", sa.String()),
    )
    # Chuyển trạng thái cũ 'running' sang 'processing' trước khi siết ràng buộc.
    bind.execute(
        sa.update(analyses_table)
        .where(analyses_table.c.status == "running")
        .values(status="processing")
    )

    _drop_check("analyses", "ck_analysis_status")
    _create_check("analyses", "ck_analysis_status", ANALYSIS_STATUS_CHECK)
    _create_check(
        "analyses", "ck_analysis_readiness_score", ANALYSIS_READINESS_CHECK
    )

    # ------------------------------------------------------------------
    # Bảng analysis_skill_gaps (M4): đổi target_level -> required_level,
    # thêm gap_score/has_evidence/evidence/created_at.
    # ------------------------------------------------------------------
    op.add_column(
        "analysis_skill_gaps",
        sa.Column("gap_score", sa.Numeric(4, 2), nullable=True),
    )
    op.add_column(
        "analysis_skill_gaps",
        sa.Column(
            "has_evidence",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "analysis_skill_gaps",
        sa.Column("evidence", sa.Text(), nullable=True),
    )
    op.add_column(
        "analysis_skill_gaps",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # MySQL 8 không tự cập nhật check constraint khi đổi tên cột, nên phải bỏ
    # check cũ (đang tham chiếu target_level) trước khi rename.
    _drop_check("analysis_skill_gaps", "ck_analysis_skill_gap_levels")

    if _is_mysql():
        op.alter_column(
            "analysis_skill_gaps",
            "target_level",
            new_column_name="required_level",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
    else:
        with op.batch_alter_table("analysis_skill_gaps") as batch_op:
            batch_op.alter_column(
                "target_level",
                new_column_name="required_level",
                existing_type=sa.Integer(),
                existing_nullable=False,
            )

    gaps_table = sa.table(
        "analysis_skill_gaps",
        sa.column("current_level", sa.Integer()),
        sa.column("required_level", sa.Integer()),
        sa.column("gap_score", sa.Numeric(4, 2)),
    )
    # gap_score = max(0, required_level - current_level) cho dữ liệu cũ.
    gap_expression = sa.case(
        (
            gaps_table.c.required_level > gaps_table.c.current_level,
            gaps_table.c.required_level - gaps_table.c.current_level,
        ),
        else_=sa.literal(0),
    )
    bind.execute(sa.update(gaps_table).values(gap_score=gap_expression))

    # Sau khi backfill mới bắt buộc gap_score NOT NULL.
    if _is_mysql():
        op.alter_column(
            "analysis_skill_gaps",
            "gap_score",
            existing_type=sa.Numeric(4, 2),
            nullable=False,
        )
    else:
        with op.batch_alter_table("analysis_skill_gaps") as batch_op:
            batch_op.alter_column(
                "gap_score",
                existing_type=sa.Numeric(4, 2),
                nullable=False,
            )

    _create_check(
        "analysis_skill_gaps", "ck_analysis_skill_gap_levels", SKILL_LEVELS_CHECK
    )
    _create_check(
        "analysis_skill_gaps", "ck_analysis_skill_gap_score", SKILL_GAP_SCORE_CHECK
    )

    # ------------------------------------------------------------------
    # Bảng interview_sessions (M6): thêm điểm tổng và thời điểm hoàn thành.
    # ------------------------------------------------------------------
    op.add_column(
        "interview_sessions",
        sa.Column("total_score", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "interview_sessions",
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )

    sessions_table = sa.table(
        "interview_sessions",
        sa.column("status", sa.String()),
    )
    # Phiên cũ 'ready' trở thành 'in_progress'; 'failed' trở thành 'abandoned'.
    bind.execute(
        sa.update(sessions_table)
        .where(sessions_table.c.status == "ready")
        .values(status="in_progress")
    )
    bind.execute(
        sa.update(sessions_table)
        .where(sessions_table.c.status == "failed")
        .values(status="abandoned")
    )

    _drop_check("interview_sessions", "ck_interview_sessions_status")
    _create_check(
        "interview_sessions",
        "ck_interview_sessions_status",
        INTERVIEW_STATUS_CHECK,
    )
    _create_check(
        "interview_sessions",
        "ck_interview_sessions_total_score",
        INTERVIEW_TOTAL_SCORE_CHECK,
    )

    # ------------------------------------------------------------------
    # Bảng interview_answers (M6): mỗi câu hỏi tối đa một câu trả lời.
    # ------------------------------------------------------------------
    op.create_table(
        "interview_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
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
        sa.UniqueConstraint(
            "question_id", name="uq_interview_answers_question_id"
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_interview_answers_score",
        ),
        **MYSQL_TABLE_ARGS,
    )
    op.create_index(
        "ix_interview_answers_question_id",
        "interview_answers",
        ["question_id"],
    )


def downgrade() -> None:
    """Hoàn tác các thay đổi M4/M6 theo thứ tự an toàn."""
    bind = op.get_bind()

    op.drop_index(
        "ix_interview_answers_question_id",
        table_name="interview_answers",
    )
    op.drop_table("interview_answers")

    # ------------------------------------------------------------------
    # interview_sessions: trả trạng thái cũ và bỏ cột mới.
    # ------------------------------------------------------------------
    _drop_check("interview_sessions", "ck_interview_sessions_total_score")
    _drop_check("interview_sessions", "ck_interview_sessions_status")

    sessions_table = sa.table(
        "interview_sessions",
        sa.column("status", sa.String()),
    )
    bind.execute(
        sa.update(sessions_table)
        .where(sessions_table.c.status == "abandoned")
        .values(status="failed")
    )

    _create_check(
        "interview_sessions",
        "ck_interview_sessions_status",
        OLD_INTERVIEW_STATUS_CHECK,
    )
    op.drop_column("interview_sessions", "completed_at")
    op.drop_column("interview_sessions", "total_score")

    # ------------------------------------------------------------------
    # analysis_skill_gaps: bỏ cột mới và đổi required_level về target_level.
    # ------------------------------------------------------------------
    _drop_check("analysis_skill_gaps", "ck_analysis_skill_gap_score")
    _drop_check("analysis_skill_gaps", "ck_analysis_skill_gap_levels")

    if _is_mysql():
        op.alter_column(
            "analysis_skill_gaps",
            "gap_score",
            existing_type=sa.Numeric(4, 2),
            nullable=True,
        )
        op.alter_column(
            "analysis_skill_gaps",
            "required_level",
            new_column_name="target_level",
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
    else:
        with op.batch_alter_table("analysis_skill_gaps") as batch_op:
            batch_op.alter_column(
                "gap_score",
                existing_type=sa.Numeric(4, 2),
                nullable=True,
            )
            batch_op.alter_column(
                "required_level",
                new_column_name="target_level",
                existing_type=sa.Integer(),
                existing_nullable=False,
            )

    _create_check(
        "analysis_skill_gaps", "ck_analysis_skill_gap_levels", OLD_SKILL_LEVELS_CHECK
    )
    op.drop_column("analysis_skill_gaps", "created_at")
    op.drop_column("analysis_skill_gaps", "evidence")
    op.drop_column("analysis_skill_gaps", "has_evidence")
    op.drop_column("analysis_skill_gaps", "gap_score")

    # ------------------------------------------------------------------
    # analyses: trả trạng thái cũ và bỏ cột mới.
    # ------------------------------------------------------------------
    _drop_check("analyses", "ck_analysis_readiness_score")
    _drop_check("analyses", "ck_analysis_status")

    analyses_table = sa.table(
        "analyses",
        sa.column("status", sa.String()),
    )
    bind.execute(
        sa.update(analyses_table)
        .where(analyses_table.c.status == "processing")
        .values(status="running")
    )

    _create_check("analyses", "ck_analysis_status", OLD_ANALYSIS_STATUS_CHECK)
    op.drop_column("analyses", "failure_reason")
    op.drop_column("analyses", "benchmark_date")
    op.drop_column("analyses", "market_source")
    op.drop_column("analyses", "readiness_score")
