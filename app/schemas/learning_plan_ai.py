from pydantic import Field

from app.schemas.ai.common import AIStructuredResponse


class ResourceSelection(AIStructuredResponse):
    skill_id: int = Field(gt=0)
    week_number: int = Field(ge=1, le=4)
    resource_id: int | None = Field(default=None, gt=0)


class ResourceSelectionResponse(AIStructuredResponse):
    selections: list[ResourceSelection] = Field(min_length=1, max_length=32)
