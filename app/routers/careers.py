from fastapi import APIRouter, Path, Query

from app.core.deps import DbSession
from app.schemas.auth import ApiResponse
from app.schemas.catalog import CareerRoleRead, CareerRoleSkillRead
from app.services.catalog_service import get_role_by_id, get_role_skills, list_roles

router = APIRouter(prefix="/api/v1/careers", tags=["careers"])


@router.get("", response_model=ApiResponse[list[CareerRoleRead]])
def get_careers(
    db: DbSession,
    category_id: int | None = Query(default=None, gt=0),
    level: str | None = Query(default=None, max_length=50),
) -> ApiResponse[list[CareerRoleRead]]:
    return ApiResponse(
        data=list_roles(db, category_id=category_id, level=level),
        message="Career roles retrieved",
    )


@router.get("/{career_id}", response_model=ApiResponse[CareerRoleRead])
def get_career_detail(
    db: DbSession,
    career_id: int = Path(gt=0),
) -> ApiResponse[CareerRoleRead]:
    return ApiResponse(
        data=get_role_by_id(db, career_id),
        message="Career role retrieved",
    )


@router.get("/{career_id}/skills", response_model=ApiResponse[list[CareerRoleSkillRead]])
def get_career_skills(
    db: DbSession,
    career_id: int = Path(gt=0),
) -> ApiResponse[list[CareerRoleSkillRead]]:
    return ApiResponse(
        data=get_role_skills(db, career_id),
        message="Career role skills retrieved",
    )

