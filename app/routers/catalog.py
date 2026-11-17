from fastapi import APIRouter, Path, Query

from app.core.deps import DbSession
from app.schemas.auth import ApiResponse
from app.schemas.catalog import (
    CareerRoleRead,
    CareerRoleSkillRead,
    CategoryRead,
    LearningResourceRead,
    ResourceType,
    SkillRead,
)
from app.services.catalog_service import (
    get_approved_resource,
    get_role_by_id,
    get_role_skills,
    list_categories,
    list_resources,
    list_roles,
    list_skills,
    serialize_learning_resource,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


@router.get("/categories", response_model=ApiResponse[list[CategoryRead]])
def get_categories(db: DbSession):
    return ApiResponse(data=list_categories(db), message="Career categories retrieved")


@router.get("/roles", response_model=ApiResponse[list[CareerRoleRead]])
def get_roles(
    db: DbSession,
    category_id: int | None = Query(default=None, gt=0),
    level: str | None = Query(default=None, max_length=50),
):
    return ApiResponse(
        data=list_roles(db, category_id=category_id, level=level),
        message="Career roles retrieved",
    )


@router.get("/roles/{role_id}", response_model=ApiResponse[CareerRoleRead])
def get_role_detail(db: DbSession, role_id: int = Path(gt=0)):
    return ApiResponse(
        data=get_role_by_id(db, role_id),
        message="Career role retrieved",
    )


@router.get(
    "/roles/{role_id}/skills",
    response_model=ApiResponse[list[CareerRoleSkillRead]],
)
def get_catalog_role_skills(db: DbSession, role_id: int = Path(gt=0)):
    return ApiResponse(
        data=get_role_skills(db, role_id),
        message="Career role skills retrieved",
    )


@router.get("/skills", response_model=ApiResponse[list[SkillRead]])
def get_skills(
    db: DbSession,
    search: str | None = Query(default=None, max_length=100),
    category_id: int | None = Query(default=None, gt=0),
    role_id: int | None = Query(default=None, gt=0),
):
    """Tìm kiếm và lọc danh mục kỹ năng chuẩn theo từ khóa, phân nhóm (category) hoặc vị trí (role)."""
    return ApiResponse(
        data=list_skills(
            db, search=search, category_id=category_id, role_id=role_id
        ),
        message="Skills retrieved",
    )


@router.get("/resources", response_model=ApiResponse[list[LearningResourceRead]])
def get_resources(
    db: DbSession,
    skill_id: int | None = Query(default=None, gt=0),
    role_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=100),
    resource_type: ResourceType | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    return ApiResponse(
        data=[
            serialize_learning_resource(item)
            for item in list_resources(
                db,
                skill_id=skill_id,
                role_id=role_id,
                search=search,
                resource_type=resource_type,
                limit=limit,
            )
        ],
        message="Learning resources retrieved",
    )


@router.get(
    "/resources/{resource_id}",
    response_model=ApiResponse[LearningResourceRead],
)
def get_resource(db: DbSession, resource_id: int = Path(gt=0)):
    resource = get_approved_resource(db, resource_id)
    return ApiResponse(
        data=serialize_learning_resource(resource),
        message="Learning resource retrieved",
    )
