from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import ApiResponse

SUPPORTED_PURPOSE_VERSION: Literal["v1"] = "v1"


class AIConsent(BaseModel):
    accepted: bool
    purpose_version: str = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid")


class AnalysisRequest(BaseModel):
    cv_id: int | None = Field(default=None, ge=1)
    career_role_id: int = Field(ge=1)
    ai_consent: AIConsent

    model_config = ConfigDict(extra="forbid")


SourceType = Literal["profile", "cv", "cv_and_profile"]
AnalysisStatus = Literal["pending", "running", "completed", "failed"]


class AnalysisAcceptedData(BaseModel):
    id: int
    status: Literal["pending"] = "pending"
    status_url: str


class AnalysisSkillGapRead(BaseModel):
    skill_id: int
    skill_name: str
    current_level: int
    target_level: int
    gap: int
    is_required: bool
    weight: float
    recommendation: str | None


class AnalysisResultData(BaseModel):
    id: int
    status: AnalysisStatus
    source_type: SourceType
    career_role_id: int | None
    readiness_score: int | None
    summary: str | None
    skill_gaps: list[AnalysisSkillGapRead]
    created_at: datetime
    completed_at: datetime | None


AnalysisAcceptedResponse = ApiResponse[AnalysisAcceptedData]
AnalysisResultResponse = ApiResponse[AnalysisResultData]
