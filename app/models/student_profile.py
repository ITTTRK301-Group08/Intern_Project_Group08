from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.career import CareerRole
    from app.models.profile_data import ProfileSkill, ProfileStrength
    from app.models.user import User


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    major: Mapped[str | None] = mapped_column(String(150), nullable=True)
    university: Mapped[str | None] = mapped_column(String(200), nullable=True)
    career_goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("career_roles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user: Mapped["User"] = relationship("User", back_populates="student_profile")
    target_role: Mapped["CareerRole | None"] = relationship("CareerRole")
    strength_items: Mapped[list["ProfileStrength"]] = relationship(
        "ProfileStrength",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileStrength.id",
    )
    skill_assessments: Mapped[list["ProfileSkill"]] = relationship(
        "ProfileSkill",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProfileSkill.id",
    )

    @property
    def strengths(self) -> list[str]:
        return [item.strength for item in self.strength_items]

    @property
    def self_assessed_skills(self) -> list[dict[str, str | int]]:
        return [
            {"skill_name": item.skill.name, "level": item.level}
            for item in self.skill_assessments
        ]

    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }
