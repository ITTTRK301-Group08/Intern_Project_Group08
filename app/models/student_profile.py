from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    major: Mapped[str | None] = mapped_column(String(150), nullable=True)
    university: Mapped[str | None] = mapped_column(String(200), nullable=True)
    strengths: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    self_assessed_skills: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    career_goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # career_roles (M3) is not implemented in Task 2; keep nullable int without FK for compatibility.
    target_role_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user: Mapped["User"] = relationship("User", back_populates="student_profile")
