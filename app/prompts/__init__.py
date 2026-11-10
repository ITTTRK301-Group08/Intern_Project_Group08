"""Các prompt dùng cho nghiệp vụ AI."""

from app.prompts.mock_interview import (
    MOCK_INTERVIEW_SYSTEM_INSTRUCTION,
    InterviewSkillContext,
    build_mock_interview_prompt,
)

__all__ = [
    "MOCK_INTERVIEW_SYSTEM_INSTRUCTION",
    "InterviewSkillContext",
    "build_mock_interview_prompt",
]
