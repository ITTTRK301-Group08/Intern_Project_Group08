from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.auth import ApiResponse

T = TypeVar("T")


class SkillAssessmentSchema(BaseModel):
    skill_name: Annotated[str, Field(min_length=1, max_length=150)]
    level: Annotated[int, Field(ge=0, le=5)]

    @field_validator("skill_name")
    @classmethod
    def skill_name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("skill_name must not be empty")
        return stripped


class ProfileUpdateRequest(BaseModel):
    full_name: Annotated[str, Field(min_length=1, max_length=150)]
    major: str | None = Field(default=None, max_length=150)
    university: str | None = Field(default=None, max_length=200)
    strengths: list[Annotated[str, Field(min_length=1, max_length=100)]] | None = None
    self_assessed_skills: list[SkillAssessmentSchema] | None = None
    career_goal: str | None = Field(default=None, max_length=255)
    target_role_id: int | None = Field(default=None, ge=1)
    bio: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("full_name must not be empty")
        return stripped

    @field_validator("strengths")
    @classmethod
    def strengths_not_blank(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for item in value:
            stripped = item.strip()
            if not stripped:
                raise ValueError("strength items must not be empty")
            cleaned.append(stripped)
        return cleaned


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    email: EmailStr | None = None
    full_name: str
    major: str | None = None
    university: str | None = None
    strengths: list[str] | None = None
    self_assessed_skills: list[dict[str, Any]] | None = None
    career_goal: str | None = None
    target_role_id: int | None = None
    bio: str | None = None
    updated_at: Any = None

    model_config = ConfigDict(from_attributes=True)


ProfileApiResponse = ApiResponse[ProfileResponse]
