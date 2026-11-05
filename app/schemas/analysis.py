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
