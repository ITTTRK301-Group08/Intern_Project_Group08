from pydantic import Field

from app.schemas.ai.common import AIStructuredResponse


class AnalysisSkillAssessment(AIStructuredResponse):
    skill_id: int = Field(gt=0)
    current_level: int = Field(ge=0, le=5)
    evidence: str | None = Field(default=None, max_length=1200)
    recommendation: str | None = Field(default=None, max_length=2000)


class AnalysisAIResponse(AIStructuredResponse):
    skills: list[AnalysisSkillAssessment] = Field(min_length=1, max_length=32)
