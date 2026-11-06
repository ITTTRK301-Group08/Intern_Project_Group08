from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
    from app.models.career import CareerRole, Skill
    from app.models.cv import CV
    from app.models.user import User


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    cv_id: Mapped[int | None] = mapped_column(
        ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True
    )
    career_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("career_roles.id", ondelete="SET NULL"), nullable=True
    )
    consent_accepted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    consent_purpose_version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User")
    cv: Mapped["CV | None"] = relationship("CV")
    career_role: Mapped["CareerRole | None"] = relationship("CareerRole")
    skill_gaps: Mapped[list["AnalysisSkillGap"]] = relationship(
        "AnalysisSkillGap", back_populates="analysis", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("consent_accepted = 1", name="ck_analysis_consent_accepted"),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')",
            name="ck_analysis_status",
        ),
        Index("ix_analyses_user_created", "user_id", "created_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )


class AnalysisSkillGap(Base):
    __tablename__ = "analysis_skill_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False
    )
    current_level: Mapped[int] = mapped_column(Integer, nullable=False)
    target_level: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="skill_gaps"
    )
    skill: Mapped["Skill"] = relationship("Skill")

    __table_args__ = (
        UniqueConstraint("analysis_id", "skill_id", name="uq_analysis_skill_gap"),
        CheckConstraint(
            "current_level >= 0 AND current_level <= 5 "
            "AND target_level >= 0 AND target_level <= 5 "
            "AND target_level >= current_level",
            name="ck_analysis_skill_gap_levels",
        ),
        Index("ix_analysis_skill_gaps_skill_id", "skill_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )
