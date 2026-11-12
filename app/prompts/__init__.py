"""Các prompt dùng cho nghiệp vụ AI."""

from app.prompts.mock_interview import (
    INTERVIEW_GRADING_SYSTEM_INSTRUCTION,
    MOCK_INTERVIEW_SYSTEM_INSTRUCTION,
    InterviewSkillContext,
    build_interview_grading_prompt,
    build_mock_interview_prompt,
)
from app.prompts.skill_gap_analysis import (
    SKILL_GAP_SYSTEM_INSTRUCTION,
    SkillAnalysisContext,
    build_profile_summary,
    build_skill_gap_prompt,
)

__all__ = [
    "INTERVIEW_GRADING_SYSTEM_INSTRUCTION",
    "MOCK_INTERVIEW_SYSTEM_INSTRUCTION",
    "SKILL_GAP_SYSTEM_INSTRUCTION",
    "InterviewSkillContext",
    "SkillAnalysisContext",
    "build_interview_grading_prompt",
    "build_mock_interview_prompt",
    "build_profile_summary",
    "build_skill_gap_prompt",
]
