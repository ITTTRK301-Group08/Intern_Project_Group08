from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.career import CareerRole
    from app.models.user import User


class InterviewSession(Base):
    """Phiên phỏng vấn thử của một người dùng theo vị trí nghề nghiệp."""

    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Giữ lại phiên phỏng vấn khi vị trí nghề nghiệp bị xóa khỏi catalog.
    career_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("career_roles.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ready", server_default="ready"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user: Mapped["User"] = relationship("User")
    career_role: Mapped["CareerRole | None"] = relationship("CareerRole")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        "InterviewQuestion",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewQuestion.question_order",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('ready', 'in_progress', 'completed', 'failed')",
            name="ck_interview_sessions_status",
        ),
        Index("ix_interview_sessions_user_created", "user_id", "created_at"),
        Index("ix_interview_sessions_career_role_id", "career_role_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )


class InterviewQuestion(Base):
    """Câu hỏi phỏng vấn đã được AI sinh và xác thực."""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    competency: Mapped[str] = mapped_column(String(255), nullable=False)
    evaluation_criteria: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="questions"
    )

    __table_args__ = (
        UniqueConstraint(
            "session_id", "question_order", name="uq_interview_question_order"
        ),
        CheckConstraint(
            "question_order >= 1 AND question_order <= 3",
            name="ck_interview_questions_order",
        ),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )
