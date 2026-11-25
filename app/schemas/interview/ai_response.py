"""Schema xác thực dữ liệu câu hỏi và điểm số do AI sinh ra."""

import math
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator

from app.schemas.ai import AIStructuredResponse

QuestionText = Annotated[str, Field(min_length=1, max_length=2000)]
Competency = Annotated[str, Field(min_length=1, max_length=255)]
EvaluationCriterion = Annotated[str, Field(min_length=1, max_length=500)]


class InterviewQuestionAI(AIStructuredResponse):
    """Một câu hỏi phỏng vấn cùng năng lực và tiêu chí đánh giá."""

    question_text: QuestionText
    competency: Competency
    evaluation_criteria: list[EvaluationCriterion] = Field(
        min_length=1,
        max_length=10,
    )

    @field_validator("evaluation_criteria")
    @classmethod
    def reject_blank_criteria(cls, values: list[str]) -> list[str]:
        """Từ chối tiêu chí rỗng hoặc chỉ chứa khoảng trắng."""
        normalized: list[str] = []
        for value in values:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Tiêu chí đánh giá không được rỗng.")
            normalized.append(stripped)
        return normalized


class InterviewGenerationAIResponse(AIStructuredResponse):
    """Kết quả AI sinh câu hỏi; bắt buộc có đúng 3 câu hỏi."""

    questions: list[InterviewQuestionAI] = Field(min_length=3, max_length=3)


class InterviewAnswerScoreAI(AIStructuredResponse):
    """Kết quả AI chấm một câu trả lời theo thang điểm 0–100.

    Điểm không hợp lệ (ngoài khoảng, không phải số hữu hạn) hoặc feedback
    rỗng sẽ bị từ chối thay vì tự động clamp về 0/100.
    """

    score: Annotated[Decimal, Field(ge=0, le=100)]
    feedback: Annotated[str, Field(min_length=1, max_length=4000)]

    @field_validator("score", mode="before")
    @classmethod
    def reject_non_numeric_score(cls, value: object) -> object:
        """Chỉ chấp nhận số thực/int/Decimal hữu hạn do AI trả về."""
        if isinstance(value, bool):
            raise ValueError("Điểm số phải là số, không phải boolean.")
        if not isinstance(value, (int, float, Decimal)):
            raise ValueError("Điểm số phải là số.")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Điểm số phải là số hữu hạn.")
        return value

    @field_validator("feedback")
    @classmethod
    def reject_blank_feedback(cls, value: str) -> str:
        """Từ chối feedback rỗng hoặc chỉ chứa khoảng trắng."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Feedback không được để trống.")
        return normalized
