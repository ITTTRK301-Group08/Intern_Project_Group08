"""AI provider integration point (Task 4 placeholder).

Task 4 does NOT connect to Gemini or any real AI provider.
This module exists only to define the integration boundary; it must not be
called when consent is invalid.
"""

from datetime import datetime
from typing import TypedDict


class ProfileSkillInput(TypedDict):
    skill_name: str
    level: int


class ProfileAnalysisContext(TypedDict):
    strengths: list[str]
    self_assessed_skills: list[ProfileSkillInput]
    career_goal: str | None
    bio: str | None
    profile_updated_at: datetime


def request_skill_gap_analysis(
    *,
    user_id: int,
    cv_id: int | None,
    career_role_id: int | None,
    profile_context: ProfileAnalysisContext | None = None,
) -> None:
    raise NotImplementedError("AI analysis pipeline is not implemented (Task 4 consent gate only)")
