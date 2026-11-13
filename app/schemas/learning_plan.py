from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import ApiResponse


class LearningPlanCreateRequest(BaseModel):
    analysis_id: int = Field(gt=0, description="ID của báo cáo phân tích đã hoàn thành")
    title: str | None = Field(default=None, max_length=255, description="Tiêu đề lộ trình tùy chỉnh")
    duration_days: int = Field(default=30, ge=7, le=60, description="Thời lượng lộ trình theo ngày")

    model_config = ConfigDict(extra="forbid")


class LearningPlanStatusUpdateRequest(BaseModel):
    status: Literal["active", "completed", "archived"] = Field(
        description="Trạng thái mới của lộ trình: active, completed, archived"
    )

    model_config = ConfigDict(extra="forbid")


class LearningPlanItemUpdateRequest(BaseModel):
    is_completed: bool = Field(description="Đánh dấu đã hoàn thành hoặc chưa hoàn thành")

    model_config = ConfigDict(extra="forbid")


class ResourceBrief(BaseModel):
    id: int
    title: str
    provider: str
    url: str
    resource_type: str
    language: str = "en"
    is_free: bool = True

    model_config = ConfigDict(from_attributes=True)


class LearningPlanItemResponse(BaseModel):
    id: int
    plan_id: int
    skill_id: int
    skill_name: str
    resource_id: int | None = None
    resource: ResourceBrief | None = None
    week_number: int
    task_description: str
    estimated_hours: float | None = None
    is_completed: bool
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LearningPlanSummaryResponse(BaseModel):
    id: int
    user_id: int
    analysis_id: int
    target_role: str | None = None
    title: str
    start_date: date
    end_date: date
    status: str
    created_at: datetime
    total_items: int = 0
    completed_items: int = 0
    progress_percent: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class LearningPlanResponse(LearningPlanSummaryResponse):
    items: list[LearningPlanItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


LearningPlanApiResponse = ApiResponse[LearningPlanResponse]
LearningPlanListApiResponse = ApiResponse[list[LearningPlanSummaryResponse]]
LearningPlanItemApiResponse = ApiResponse[LearningPlanItemResponse]
