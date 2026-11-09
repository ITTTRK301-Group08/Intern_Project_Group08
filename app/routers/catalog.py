from fastapi import APIRouter, Query

from app.core.deps import DbSession
from app.schemas.auth import ApiResponse
from app.schemas.catalog import (
    CareerRoleRead,
    CategoryRead,
    LearningResourceRead,
    SkillRead,
)
from app.services.catalog_service import (
    list_categories,
    list_resources,
    list_roles,
    list_skills,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/categories", response_model=ApiResponse[list[CategoryRead]])
def get_categories(db: DbSession):
    return ApiResponse(data=list_categories(db), message="Career categories retrieved")


@router.get("/roles", response_model=ApiResponse[list[CareerRoleRead]])
def get_roles(
    db: DbSession,
    category_id: int | None = Query(default=None, gt=0),
):
    return ApiResponse(
        data=list_roles(db, category_id=category_id),
        message="Career roles retrieved",
    )


@router.get("/skills", response_model=ApiResponse[list[SkillRead]])
def get_skills(
    db: DbSession,
    search: str | None = Query(default=None, max_length=100),
):
    return ApiResponse(data=list_skills(db, search=search), message="Skills retrieved")


@router.get("/resources", response_model=ApiResponse[list[LearningResourceRead]])
def get_resources(
    db: DbSession,
    skill_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
):
    return ApiResponse(
        data=list_resources(
            db, skill_id=skill_id, search=search, limit=limit
        ),
        message="Learning resources retrieved",
    )
