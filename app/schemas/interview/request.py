"""Schema request tạo phiên phỏng vấn thử và gửi câu trả lời."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.analysis import AIConsent

# Giới hạn độ dài câu trả lời thống nhất cho toàn bộ nghiệp vụ M6.
ANSWER_MAX_LENGTH = 5000


class InterviewCreateRequest(BaseModel):
    """Yêu cầu tạo phiên phỏng vấn theo vị trí nghề nghiệp.

    Không có trường `user_id`: định danh người dùng luôn lấy từ JWT hiện tại.
    `ai_consent` bắt buộc để tuân thủ chính sách AI Consent của dự án.
    """

    career_role_id: int = Field(gt=0)
    ai_consent: AIConsent

    model_config = ConfigDict(extra="forbid")


class InterviewAnswerSubmitRequest(BaseModel):
    """Câu trả lời của sinh viên cho một câu hỏi thuộc phiên hiện tại."""

    question_id: int = Field(gt=0)
    answer_text: str = Field(min_length=1, max_length=ANSWER_MAX_LENGTH)

    @field_validator("answer_text")
    @classmethod
    def reject_blank_answer(cls, value: str) -> str:
        """Từ chối câu trả lời rỗng hoặc chỉ chứa khoảng trắng."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Câu trả lời không được để trống.")
        return normalized

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
