from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.auth import ApiResponse


class CVExtractionWarning(BaseModel):
    code: str
    cause: str
    guidance: str
    recommended_actions: list[str]
    profile_url: str = "/profile"
    analysis_url: str = "/analysis?source=profile"


class CVResponse(BaseModel):
    id: int
    file_name: str
    file_size: int
    mime_type: str
    extracted_text: str | None = None
    is_active: bool
    created_at: datetime
    has_text: bool = False
    extraction_status: str = "no_text"
    has_analysis: bool = False
    analysis_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CVUploadData(BaseModel):
    cv: CVResponse
    has_text: bool = True
    warning: CVExtractionWarning | None = None


class CVListData(BaseModel):
    cvs: list[CVResponse]
    total: int


class CVDetailData(BaseModel):
    cv: CVResponse
    warning: CVExtractionWarning | None = None


class CVDeleteData(BaseModel):
    cv_id: int
    deleted: bool = True
    deletion_type: Literal["soft", "hard"]
    is_active: bool
    has_analysis: bool
    analysis_count: int


CVUploadResponse = ApiResponse[CVUploadData]
CVListResponse = ApiResponse[CVListData]
CVDetailResponse = ApiResponse[CVDetailData]
CVDeleteResponse = ApiResponse[CVDeleteData]
