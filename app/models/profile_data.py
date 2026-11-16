from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.career import CareerRole, Skill
    from app.models.student_profile import StudentProfile


class ProfileStrength(Base):
    __tablename__ = "profile_strengths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False
    )
    strength: Mapped[str] = mapped_column(String(100), nullable=False)

    profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile", back_populates="strength_items"
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "strength", name="uq_profile_strength"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )


class ProfileSkill(Base):
    __tablename__ = "profile_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    profile: Mapped["StudentProfile"] = relationship(
        "StudentProfile", back_populates="skill_assessments"
    )
    skill: Mapped["Skill"] = relationship("Skill")

    __table_args__ = (
        UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill"),
        CheckConstraint("level >= 0 AND level <= 5", name="ck_profile_skill_level"),
        Index("ix_profile_skills_skill_id", "skill_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )


class CareerRoleSkill(Base):
    __tablename__ = "career_role_skills"

    career_role_id: Mapped[int] = mapped_column(
        ForeignKey("career_roles.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), primary_key=True
    )
    required_level: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    weight: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0, server_default="1.0"
    )

    career_role: Mapped["CareerRole"] = relationship(
        "CareerRole", back_populates="required_skills"
    )
    skill: Mapped["Skill"] = relationship("Skill", back_populates="career_roles")

    __table_args__ = (
        CheckConstraint(
            "required_level >= 0 AND required_level <= 5",
            name="ck_career_role_skill_level",
        ),
        CheckConstraint(
            "weight > 0",
            name="ck_career_role_skill_weight",
        ),
        Index("ix_career_role_skills_skill_id", "skill_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )
