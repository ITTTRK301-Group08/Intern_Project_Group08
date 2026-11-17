"""Schema xác thực dữ liệu câu hỏi phỏng vấn do AI sinh ra."""

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
