from datetime import date, datetime
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
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.career import Skill
    from app.models.learning_resource import LearningResource
    from app.models.user import User


class LearningPlan(Base):
    """Lộ trình học tập cá nhân hóa 30 ngày (hoặc 4-8 tuần) được sinh từ báo cáo phân tích."""

    __tablename__ = "learning_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    user: Mapped["User"] = relationship("User")
    analysis: Mapped["Analysis"] = relationship("Analysis")
    items: Mapped[list["LearningPlanItem"]] = relationship(
        "LearningPlanItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="LearningPlanItem.week_number, LearningPlanItem.id",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_learning_plan_status",
        ),
        Index("ix_learning_plans_user_status", "user_id", "status"),
        Index("ix_learning_plans_analysis", "analysis_id"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )


class LearningPlanItem(Base):
    """Nhiệm vụ học tập cụ thể trong lộ trình theo từng tuần."""

    __tablename__ = "learning_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False
    )
    resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_resources.id", ondelete="SET NULL"), nullable=True
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    plan: Mapped["LearningPlan"] = relationship("LearningPlan", back_populates="items")
    skill: Mapped["Skill"] = relationship("Skill")
    resource: Mapped["LearningResource | None"] = relationship("LearningResource")

    __table_args__ = (
        CheckConstraint(
            "week_number >= 1 AND week_number <= 8",
            name="ck_learning_plan_item_week",
        ),
        Index("ix_learning_plan_items_plan_week", "plan_id", "week_number"),
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_0900_ai_ci",
        },
    )
