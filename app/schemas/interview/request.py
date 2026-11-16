"""Schema request tạo phiên phỏng vấn thử."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis import AIConsent


class InterviewCreateRequest(BaseModel):
    """Yêu cầu tạo phiên phỏng vấn theo vị trí nghề nghiệp.

    Không có trường `user_id`: định danh người dùng luôn lấy từ JWT hiện tại.
    `ai_consent` bắt buộc để tuân thủ chính sách AI Consent của dự án.
    """

    career_role_id: int = Field(gt=0)
    ai_consent: AIConsent

    model_config = ConfigDict(extra="forbid")
