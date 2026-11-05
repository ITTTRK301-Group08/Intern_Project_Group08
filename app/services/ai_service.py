"""AI provider integration point (Task 4 placeholder).

Task 4 does NOT connect to Gemini or any real AI provider.
This module exists only to define the integration boundary; it must not be
called when consent is invalid and is not invoked in Task 4's consent-only flow.
"""


def request_skill_gap_analysis(*, user_id: int, cv_id: int | None, career_role_id: int | None) -> None:
    raise NotImplementedError("AI analysis pipeline is not implemented (Task 4 consent gate only)")
