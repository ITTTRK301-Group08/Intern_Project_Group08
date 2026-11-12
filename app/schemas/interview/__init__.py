"""Các schema của nghiệp vụ phỏng vấn thử."""

from app.schemas.interview.ai_response import (
    InterviewAnswerGradeAI,
    InterviewGenerationAIResponse,
    InterviewQuestionAI,
)
from app.schemas.interview.request import (
    InterviewAnswerCreateRequest,
    InterviewCreateRequest,
)
from app.schemas.interview.response import (
    InterviewAnswerRead,
    InterviewAnswerResponse,
    InterviewCareerRoleRead,
    InterviewHistoryData,
    InterviewHistoryResponse,
    InterviewQuestionRead,
    InterviewQuestionsData,
    InterviewQuestionsResponse,
    InterviewSessionRead,
    InterviewSessionResponse,
    InterviewSummaryRead,
    InterviewSummaryResponse,
)

__all__ = [
    "InterviewAnswerCreateRequest",
    "InterviewAnswerGradeAI",
    "InterviewAnswerRead",
    "InterviewAnswerResponse",
    "InterviewCareerRoleRead",
    "InterviewCreateRequest",
    "InterviewGenerationAIResponse",
    "InterviewHistoryData",
    "InterviewHistoryResponse",
    "InterviewQuestionAI",
    "InterviewQuestionRead",
    "InterviewQuestionsData",
    "InterviewQuestionsResponse",
    "InterviewSessionRead",
    "InterviewSessionResponse",
    "InterviewSummaryRead",
    "InterviewSummaryResponse",
]
