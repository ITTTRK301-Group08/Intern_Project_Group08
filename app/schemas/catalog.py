from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ResourceType = Literal["documentation", "course", "video", "article", "practice"]
Slug = Annotated[str, Field(min_length=2, max_length=180, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class CategoryWrite(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=120)]
    slug: Annotated[str, Field(min_length=2, max_length=140, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class CategoryRead(CategoryWrite):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequiredSkillWrite(BaseModel):
    skill_id: int = Field(gt=0)
    required_level: int = Field(default=3, ge=0, le=5)

    model_config = ConfigDict(extra="forbid")


class SkillRead(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CareerRoleWrite(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    name: Annotated[str, Field(min_length=1, max_length=150)]
    slug: Annotated[str, Field(min_length=2, max_length=170, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
    description: str | None = None
    is_active: bool = True
    required_skills: list[RequiredSkillWrite] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def unique_skill_ids(self) -> "CareerRoleWrite":
        skill_ids = [item.skill_id for item in self.required_skills]
        if len(skill_ids) != len(set(skill_ids)):
            raise ValueError("required_skills cannot contain duplicate skill_id values")
        return self


class CareerRoleSkillRead(BaseModel):
    required_level: int
    skill: SkillRead

    model_config = ConfigDict(from_attributes=True)


class CareerRoleRead(BaseModel):
    id: int
    category_id: int | None
    name: str
    slug: str
    description: str | None
    is_active: bool
    category: CategoryRead | None
    required_skills: list[CareerRoleSkillRead]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkillWrite(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=150)]
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class LearningResourceWrite(BaseModel):
    slug: Slug
    skill_id: int | None = Field(default=None, gt=0)
    title: Annotated[str, Field(min_length=1, max_length=200)]
    provider: Annotated[str, Field(min_length=1, max_length=120)]
    url: Annotated[str, Field(min_length=8, max_length=1000)]
    resource_type: ResourceType
    description: str | None = None
    language: Annotated[str, Field(min_length=2, max_length=20)] = "en"
    is_free: bool = True
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("url")
    @classmethod
    def require_http_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        return value


class LearningResourceRead(LearningResourceWrite):
    id: int
    skill: SkillRead | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
