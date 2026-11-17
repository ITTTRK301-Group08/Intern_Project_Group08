"""Các schema của nghiệp vụ phỏng vấn thử."""

from app.schemas.interview.ai_response import (
    InterviewAnswerScoreAI,
    InterviewGenerationAIResponse,
    InterviewQuestionAI,
)
from app.schemas.interview.request import (
    ANSWER_MAX_LENGTH,
    InterviewAnswerSubmitRequest,
    InterviewCreateRequest,
)
from app.schemas.interview.response import (
    InterviewAnswerRead,
    InterviewAnswerResultRead,
    InterviewAnswerResultResponse,
    InterviewCareerRoleRead,
    InterviewCompletionRead,
    InterviewCompletionResponse,
    InterviewQuestionRead,
    InterviewQuestionsResponse,
    InterviewSessionDetailResponse,
    InterviewSessionListData,
    InterviewSessionListResponse,
    InterviewSessionRead,
    InterviewSessionResponse,
    InterviewSessionSummaryRead,
)

__all__ = [
    "ANSWER_MAX_LENGTH",
    "InterviewAnswerRead",
    "InterviewAnswerResultRead",
    "InterviewAnswerResultResponse",
    "InterviewAnswerScoreAI",
    "InterviewAnswerSubmitRequest",
    "InterviewCareerRoleRead",
    "InterviewCompletionRead",
    "InterviewCompletionResponse",
    "InterviewCreateRequest",
    "InterviewGenerationAIResponse",
    "InterviewQuestionAI",
    "InterviewQuestionRead",
    "InterviewQuestionsResponse",
    "InterviewSessionDetailResponse",
    "InterviewSessionListData",
    "InterviewSessionListResponse",
    "InterviewSessionRead",
    "InterviewSessionResponse",
    "InterviewSessionSummaryRead",
]
