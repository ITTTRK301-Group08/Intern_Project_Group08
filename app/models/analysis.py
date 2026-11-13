"""Model báo cáo phân tích kỹ năng (M4).

Báo cáo được tạo ở trạng thái ``processing`` rồi cập nhật bởi tác vụ nền.
Không lưu kết quả từng phần: chỉ khi toàn bộ kỹ năng đã được tính và ghi
trong cùng một transaction thì báo cáo mới chuyển sang ``completed``.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.career import CareerRole, Skill
    from app.models.cv import CV
    from app.models.user import User


class Analysis(Base):
    """Báo cáo phân tích khoảng cách kỹ năng của một người dùng."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    cv_id: Mapped[int | None] = mapped_column(
        ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )
    # Nullable ở tầng DB để giữ lịch sử nếu vị trí bị xóa; API bắt buộc chọn vị trí.
    career_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("career_roles.id", ondelete="SET NULL"), nullable=True
    )
    consent_accepted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    consent_purpose_version: Mapped[str] = mapped_column(String(20), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="profile", server_default="profile"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
<<<<<<< HEAD
    readiness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
=======
    readiness_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    market_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    benchmark_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Chỉ lưu mã lỗi an toàn, không lưu stack trace hay dữ liệu nhạy cảm.
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User")
    cv: Mapped["CV | None"] = relationship("CV")
    career_role: Mapped["CareerRole | None"] = relationship("CareerRole")
    skill_gaps: Mapped[list["AnalysisSkillGap"]] = relationship(
        "AnalysisSkillGap",
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="AnalysisSkillGap.id",
    )

    __table_args__ = (
        CheckConstraint("consent_accepted = 1", name="ck_analysis_consent_accepted"),
        CheckConstraint(
<<<<<<< HEAD
            "source_type IN ('profile', 'cv', 'cv_and_profile')",
            name="ck_analysis_source_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_analysis_status",
        ),
        CheckConstraint(
            "readiness_score IS NULL OR "
            "(readiness_score >= 0 AND readiness_score <= 100)",
=======
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_analysis_status",
        ),
        CheckConstraint(
            "readiness_score IS NULL OR (readiness_score >= 0 AND readiness_score <= 100)",
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
            name="ck_analysis_readiness_score",
        ),
        Index("ix_analyses_user_created", "user_id", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )


class AnalysisSkillGap(Base):
    """Kết quả đánh giá một kỹ năng trong báo cáo phân tích."""

    __tablename__ = "analysis_skill_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False
    )
    current_level: Mapped[int] = mapped_column(Integer, nullable=False)
<<<<<<< HEAD
    target_level: Mapped[int] = mapped_column(Integer, nullable=False)
    gap: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    weight: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, server_default="1"
    )
=======
    required_level: Mapped[int] = mapped_column(Integer, nullable=False)
    # gap_score = max(0, required_level - current_level), do backend tính.
    gap_score: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    has_evidence: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="skill_gaps"
    )
    skill: Mapped["Skill"] = relationship("Skill")

    __table_args__ = (
        UniqueConstraint("analysis_id", "skill_id", name="uq_analysis_skill_gap"),
        CheckConstraint(
            "current_level >= 0 AND current_level <= 5 "
<<<<<<< HEAD
            "AND target_level >= 0 AND target_level <= 5",
            name="ck_analysis_skill_gap_levels",
        ),
        CheckConstraint(
            "(target_level >= current_level AND gap = target_level - current_level) "
            "OR (target_level < current_level AND gap = 0)",
            name="ck_analysis_skill_gap_value",
        ),
        CheckConstraint("weight > 0", name="ck_analysis_skill_gap_weight"),
=======
            "AND required_level >= 0 AND required_level <= 5",
            name="ck_analysis_skill_gap_levels",
        ),
        CheckConstraint(
            "gap_score >= 0 AND gap_score <= 5",
            name="ck_analysis_skill_gap_score",
        ),
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
        Index("ix_analysis_skill_gaps_skill_id", "skill_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )
