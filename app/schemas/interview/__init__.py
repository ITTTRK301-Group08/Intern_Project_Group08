"""Các schema của nghiệp vụ phỏng vấn thử."""

from app.schemas.interview.ai_response import (
    InterviewGenerationAIResponse,
    InterviewQuestionAI,
)
from app.schemas.interview.request import InterviewCreateRequest
from app.schemas.interview.response import (
    InterviewCareerRoleRead,
    InterviewQuestionRead,
    InterviewSessionRead,
    InterviewSessionResponse,
)

__all__ = [
    "InterviewCareerRoleRead",
    "InterviewCreateRequest",
    "InterviewGenerationAIResponse",
    "InterviewQuestionAI",
    "InterviewQuestionRead",
    "InterviewSessionRead",
    "InterviewSessionResponse",
]
