from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.schemas.auth import ApiResponse

LearningPlanStatus = Literal["active", "completed", "archived"]


class LearningPlanStatusUpdate(BaseModel):
    status: LearningPlanStatus

    model_config = ConfigDict(extra="forbid")


class LearningPlanItemUpdate(BaseModel):
    is_completed: bool = Field(strict=True)

    model_config = ConfigDict(extra="forbid")


class LearningPlanItemRead(BaseModel):
    id: int
    skill_id: int
    week_number: int
    task_description: str
    estimated_hours: float | None
    is_completed: bool
    completed_at: datetime | None
    resource_id: int | None
    resource_title: str | None
    resource_url: str | None

    @field_serializer("completed_at")
    def serialize_completed_at(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        return utc_value.astimezone(timezone.utc)


class LearningPlanRead(BaseModel):
    id: int
    title: str
    analysis_id: int
    status: LearningPlanStatus
    start_date: date
    end_date: date
    created_at: datetime
    items: list[LearningPlanItemRead] = Field(default_factory=list)


class LearningPlanListItem(BaseModel):
    id: int
    title: str
    analysis_id: int
    status: LearningPlanStatus
    start_date: date
    end_date: date
    created_at: datetime
    item_count: int
    completed_item_count: int


class LearningPlanStatusData(BaseModel):
    id: int
    status: LearningPlanStatus


LearningPlanListResponse = ApiResponse[list[LearningPlanListItem]]
LearningPlanResponse = ApiResponse[LearningPlanRead]
LearningPlanStatusResponse = ApiResponse[LearningPlanStatusData]
LearningPlanItemResponse = ApiResponse[LearningPlanItemRead]
