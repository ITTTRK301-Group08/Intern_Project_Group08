"""Các prompt dùng cho nghiệp vụ AI."""

from app.prompts.mock_interview import (
    INTERVIEW_SCORING_SYSTEM_INSTRUCTION,
    MOCK_INTERVIEW_SYSTEM_INSTRUCTION,
    InterviewAnswerContext,
    InterviewSkillContext,
    build_interview_answer_scoring_prompt,
    build_mock_interview_prompt,
)

__all__ = [
    "INTERVIEW_SCORING_SYSTEM_INSTRUCTION",
    "MOCK_INTERVIEW_SYSTEM_INSTRUCTION",
    "InterviewAnswerContext",
    "InterviewSkillContext",
    "build_interview_answer_scoring_prompt",
    "build_mock_interview_prompt",
]
