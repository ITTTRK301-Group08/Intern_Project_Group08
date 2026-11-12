"""Schema xác thực kết quả đánh giá kỹ năng do AI trả về."""

from pydantic import Field, field_validator

from app.schemas.ai import AIStructuredResponse


class SkillAssessmentAI(AIStructuredResponse):
    """Đánh giá mức kỹ năng hiện tại của một kỹ năng trong báo cáo.

    AI chỉ được cung cấp mức hiện tại và bằng chứng; backend tự tính
    ``gap_score`` và ``readiness_score`` nên schema không có hai trường này.
    """

    skill_id: int = Field(gt=0)
    current_level: int = Field(ge=0, le=5)
    has_evidence: bool
    evidence: str | None = Field(default=None, max_length=2000)
    recommendation: str | None = Field(default=None, max_length=1000)

    @field_validator("evidence", "recommendation")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        """Chuẩn hóa chuỗi rỗng thành ``None``."""
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SkillGapAnalysisAI(AIStructuredResponse):
    """Kết quả AI đánh giá toàn bộ kỹ năng của một vị trí."""

    summary: str = Field(min_length=1, max_length=4000)
    assessments: list[SkillAssessmentAI] = Field(min_length=1, max_length=100)

    @field_validator("summary")
    @classmethod
    def reject_blank_summary(cls, value: str) -> str:
        """Từ chối nhận xét tổng quan rỗng."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Nhận xét tổng quan không được rỗng.")
        return stripped
