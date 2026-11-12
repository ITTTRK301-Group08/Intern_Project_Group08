"""Schema request/response cho nghiệp vụ phân tích kỹ năng (M4)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import ApiResponse

SUPPORTED_PURPOSE_VERSION: Literal["v1"] = "v1"


class AIConsent(BaseModel):
    """Xác nhận đồng ý gửi dữ liệu cần thiết cho dịch vụ AI."""

    accepted: bool
    purpose_version: str = Field(min_length=1, max_length=20)

    model_config = ConfigDict(extra="forbid")


class AnalysisRequest(BaseModel):
    """Yêu cầu tạo báo cáo phân tích.

    ``career_role_id`` bắt buộc vì mọi báo cáo phải gắn với một vị trí mục tiêu.
    Không có trường ``user_id``: danh tính luôn lấy từ JWT hiện tại.
    """

    cv_id: int | None = Field(default=None, ge=1)
    career_role_id: int = Field(gt=0)
    ai_consent: AIConsent

    model_config = ConfigDict(extra="forbid")


class SkillBriefRead(BaseModel):
    """Thông tin tối thiểu của một kỹ năng."""

    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class AnalysisCareerRoleRead(BaseModel):
    """Thông tin tối thiểu của vị trí nghề nghiệp trong báo cáo."""

    id: int
    name: str
    level: str

    model_config = ConfigDict(from_attributes=True)


class AnalysisSkillGapRead(BaseModel):
    """Kết quả đánh giá một kỹ năng."""

    id: int
    skill_id: int
    skill: SkillBriefRead
    current_level: int
    required_level: int
    gap_score: float
    has_evidence: bool
    evidence: str | None
    recommendation: str | None

    model_config = ConfigDict(from_attributes=True)


class AnalysisRead(BaseModel):
    """Thông tin tổng quan của một báo cáo phân tích."""

    id: int
    status: str
    cv_id: int | None
    career_role: AnalysisCareerRoleRead | None
    readiness_score: float | None
    summary: str | None
    market_source: str | None
    benchmark_date: date | None
    failure_reason: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AnalysisDetailRead(AnalysisRead):
    """Báo cáo chi tiết kèm điểm từng kỹ năng."""

    skill_gaps: list[AnalysisSkillGapRead]


class AnalysisStatusRead(BaseModel):
    """Trạng thái xử lý của báo cáo dùng cho polling."""

    id: int
    status: str
    readiness_score: float | None
    failure_reason: str | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AnalysisHistoryData(BaseModel):
    """Danh sách báo cáo phân tích của người dùng hiện tại."""

    analyses: list[AnalysisRead]
    total: int


class AnalysisSkillsData(BaseModel):
    """Danh sách điểm kỹ năng của một báo cáo."""

    analysis_id: int
    skills: list[AnalysisSkillGapRead]


class AnalysisErrorData(BaseModel):
    """Mã lỗi nghiệp vụ của M4."""

    code: str


class AnalysisError(BaseModel):
    success: bool = False
    data: AnalysisErrorData
    message: str


AnalysisResponse = ApiResponse[AnalysisRead]
AnalysisDetailResponse = ApiResponse[AnalysisDetailRead]
AnalysisStatusResponse = ApiResponse[AnalysisStatusRead]
AnalysisHistoryResponse = ApiResponse[AnalysisHistoryData]
AnalysisSkillsResponse = ApiResponse[AnalysisSkillsData]
