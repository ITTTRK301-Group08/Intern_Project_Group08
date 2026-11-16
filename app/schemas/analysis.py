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
    career_role_id: int | None = Field(default=None, ge=1)
    ai_consent: AIConsent

    model_config = ConfigDict(extra="forbid")


class AnalysisGateData(BaseModel):
    consent_valid: bool = True
    pipeline_implemented: bool = False
    cv_id: int | None = None
    career_role_id: int | None = None


class AnalysisGateErrorData(BaseModel):
    code: str


class AnalysisGateError(BaseModel):
    success: bool = False
    data: AnalysisGateErrorData
    message: str

AnalysisGateResponse = ApiResponse[AnalysisGateData]


class AnalysisHistoryItem(BaseModel):
    id: int
    status: Literal["pending", "processing", "completed", "failed"]
    readiness_score: int | None
    summary: str | None
    career_role_name: str | None
    created_at: datetime
    completed_at: datetime | None


class AnalysisHistoryData(BaseModel):
    items: list[AnalysisHistoryItem]
    page: int
    page_size: int
    total: int
    pages: int


class AnalysisReport(BaseModel):
    id: int
    status: Literal["pending", "processing", "completed", "failed"]
    readiness_score: int | None
    summary: str | None
    career_role_name: str | None
    created_at: datetime
    completed_at: datetime | None


class AnalysisSkillReport(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    current_level: int = Field(ge=0, le=5)
    required_level: int = Field(ge=0, le=5)
    gap_score: int = Field(ge=0, le=5)
    evidence: str | None
    has_evidence: bool
    recommendation: str | None


AnalysisHistoryResponse = ApiResponse[AnalysisHistoryData]
AnalysisReportResponse = ApiResponse[AnalysisReport]
AnalysisSkillsResponse = ApiResponse[list[AnalysisSkillReport]]
AnalysisStatusResponse = ApiResponse[dict[str, str]]
