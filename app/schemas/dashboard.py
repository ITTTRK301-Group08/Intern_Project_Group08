from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import ApiResponse


class ActivePlanBrief(BaseModel):
    id: int
    title: str
    target_role: str | None = None
    start_date: date
    end_date: date
    days_left: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    progress_percent: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryData(BaseModel):
    readiness_score: float | None = Field(default=None, description="Điểm sẵn sàng nghề nghiệp (%)")
    target_role_id: int | None = None
    target_role: str | None = None
    target_role_level: str | None = None
    total_analyses: int = 0
    total_interviews: int = 0
    total_skills_evaluated: int = 0
    skills_matched_count: int = 0
    skills_gap_count: int = 0
    active_plan: ActivePlanBrief | None = None
    last_analyzed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SkillRadarItem(BaseModel):
    skill_id: int
    skill_name: str
    current_level: int = Field(ge=0, le=5)
    required_level: int = Field(ge=0, le=5)
    gap_score: int = Field(ge=0, description="Độ hụt kỹ năng (max(0, required - current))")
    weight: float = Field(gt=0, default=1.0)
    is_gap: bool = False

    model_config = ConfigDict(from_attributes=True)


class SkillRadarData(BaseModel):
    role_id: int | None = None
    role_name: str | None = None
    role_level: str | None = None
    overall_readiness: float = 0.0
    skills: list[SkillRadarItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class WeeklyProgressItem(BaseModel):
    week_number: int
    total_tasks: int = 0
    completed_tasks: int = 0
    progress_percent: float = 0.0


class LearningProgressData(BaseModel):
    has_active_plan: bool = False
    plan: ActivePlanBrief | None = None
    weekly_breakdown: list[WeeklyProgressItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InterviewHistoryItem(BaseModel):
    id: int
    career_role_id: int | None = None
    career_role_name: str | None = None
    status: str
    created_at: datetime
    question_count: int = 0
    answered_count: int = 0
    total_score: float | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class InterviewHistoryData(BaseModel):
    items: list[InterviewHistoryItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 1

    model_config = ConfigDict(from_attributes=True)


class ReadinessSkillPoint(BaseModel):
    skill_id: int
    skill_name: str
    current_level: int = Field(ge=0, le=5)
    required_level: int = Field(ge=0, le=5)


class ReadinessHistoryPoint(BaseModel):
    analysis_id: int
    score: int = Field(ge=0, le=100)
    analyzed_at: datetime
    career_role_name: str | None = None
    skills: list[ReadinessSkillPoint] = Field(default_factory=list)


class ReadinessHistoryStats(BaseModel):
    report_count: int
    latest_score: int | None = None
    previous_score: int | None = None
    change_since_first: int | None = None
    latest_change: int | None = None
    highest_score: int | None = None
    lowest_score: int | None = None
    trend: Literal["improving", "declining", "stable"] | None = None


class ReadinessHistoryData(BaseModel):
    points: list[ReadinessHistoryPoint] = Field(default_factory=list)
    stats: ReadinessHistoryStats


DashboardSummaryResponse = ApiResponse[DashboardSummaryData]
SkillRadarResponse = ApiResponse[SkillRadarData]
LearningProgressResponse = ApiResponse[LearningProgressData]
InterviewHistoryResponse = ApiResponse[InterviewHistoryData]
ReadinessHistoryResponse = ApiResponse[ReadinessHistoryData]
