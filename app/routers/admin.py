from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession, require_admin
from app.models.career import CareerCategory, CareerRole, Skill
from app.models.learning_resource import LearningResource
from app.models.user import User
from app.schemas.auth import ApiResponse
from app.schemas.catalog import (
    AdminCatalogData,
    AdminCategoryDetailRead,
    AdminLearningResourceDetailRead,
    AdminSystemStats,
    CatalogStatusUpdate,
    CareerRoleRead,
    CareerRoleWrite,
    CategoryRead,
    CategoryWrite,
    LearningResourceRead,
    LearningResourceReviewRequest,
    LearningResourceWrite,
    ResourceType,
    SkillRead,
    SkillWrite,
)
from app.schemas.pagination import Page
from app.schemas.user import (
    AdminUserDetailRead,
    AdminUserRead,
    UserResponse,
    UserStatusUpdate,
)
from app.services.admin_service import get_admin_user_detail, list_admin_users
from app.services.catalog_service import (
    create_item,
    delete_item,
    ensure_category_deletable,
    get_category_detail,
    get_resource_detail,
    get_role_by_id,
    list_categories,
    list_resources,
    list_roles,
    list_skills,
    paginate_categories,
    paginate_resources,
    paginate_roles,
    paginate_skills,
    save_career_role,
    set_item_active,
    update_item,
    review_resource,
    serialize_learning_resource,
    update_learning_resource,
)
from app.services.dashboard_service import get_admin_system_stats

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/users",
    response_model=ApiResponse[Page[AdminUserRead]],
)
def list_users(
    db: DbSession,
    search: str | None = Query(default=None, max_length=200),
    role: Literal["student", "admin"] | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    data = list_admin_users(
        db,
        search=search,
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=data, message="Users retrieved")


@router.get(
    "/users/{user_id}",
    response_model=ApiResponse[AdminUserDetailRead],
)
def get_user_detail(user_id: int, db: DbSession):
    return ApiResponse(
        data=get_admin_user_detail(db, user_id), message="User retrieved"
    )


@router.put(
    "/users/{user_id}/status", response_model=ApiResponse[UserResponse]
)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.id == current_user.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot lock your own account",
        )

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return ApiResponse(data=user, message="User status updated")


@router.get("/catalog", response_model=ApiResponse[AdminCatalogData])
def get_admin_catalog(db: DbSession):
    return ApiResponse(
        data=AdminCatalogData(
            categories=[CategoryRead.model_validate(item) for item in list_categories(db)],
            roles=[
                CareerRoleRead.model_validate(item)
                for item in list_roles(db, include_inactive=True)
            ],
            skills=[
                SkillRead.model_validate(item)
                for item in list_skills(db, include_inactive=True)
            ],
            resources=[
                serialize_learning_resource(item)
                for item in list_resources(
                    db,
                    include_inactive=True,
                    include_unapproved=True,
                    limit=200,
                )
            ],
        ),
        message="Admin catalog retrieved",
    )


@router.get("/stats", response_model=ApiResponse[AdminSystemStats])
def get_admin_stats(db: DbSession):
    return ApiResponse(data=get_admin_system_stats(db), message="Admin stats retrieved")


@router.get(
    "/career-categories",
    response_model=ApiResponse[Page[CategoryRead]],
)
def list_admin_categories(
    db: DbSession,
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    return ApiResponse(
        data=paginate_categories(
            db, search=search, page=page, page_size=page_size
        ),
        message="Career categories retrieved",
    )


@router.get(
    "/career-categories/{item_id}",
    response_model=ApiResponse[AdminCategoryDetailRead],
)
def get_admin_category_detail(item_id: int, db: DbSession):
    return ApiResponse(
        data=get_category_detail(db, item_id),
        message="Career category retrieved",
    )


@router.post(
    "/career-categories",
    response_model=ApiResponse[CategoryRead],
    status_code=status.HTTP_201_CREATED,
)
def create_category(payload: CategoryWrite, db: DbSession):
    item = create_item(db, CareerCategory, payload.model_dump())
    return ApiResponse(data=item, message="Career category created")


@router.put(
    "/career-categories/{item_id}", response_model=ApiResponse[CategoryRead]
)
def update_category(item_id: int, payload: CategoryWrite, db: DbSession):
    item = update_item(db, CareerCategory, item_id, payload.model_dump())
    return ApiResponse(data=item, message="Career category updated")


@router.delete(
    "/career-categories/{item_id}", response_model=ApiResponse[dict[str, bool]]
)
def delete_category(item_id: int, db: DbSession):
    ensure_category_deletable(db, item_id)
    delete_item(db, CareerCategory, item_id)
    return ApiResponse(data={"deleted": True}, message="Career category deleted")


@router.get(
    "/career-roles",
    response_model=ApiResponse[Page[CareerRoleRead]],
)
def list_admin_roles(
    db: DbSession,
    search: str | None = Query(default=None, max_length=200),
    category_id: int | None = Query(default=None, gt=0),
    level: str | None = Query(default=None, max_length=50),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    return ApiResponse(
        data=paginate_roles(
            db,
            search=search,
            category_id=category_id,
            level=level,
            is_active=is_active,
            page=page,
            page_size=page_size,
        ),
        message="Career roles retrieved",
    )


@router.get(
    "/career-roles/{item_id}",
    response_model=ApiResponse[CareerRoleRead],
)
def get_admin_role_detail(item_id: int, db: DbSession):
    return ApiResponse(
        data=get_role_by_id(db, item_id, include_inactive=True),
        message="Career role retrieved",
    )


@router.post(
    "/career-roles",
    response_model=ApiResponse[CareerRoleRead],
    status_code=status.HTTP_201_CREATED,
)
def create_role(payload: CareerRoleWrite, db: DbSession):
    item = save_career_role(db, values=payload)
    return ApiResponse(data=item, message="Career role created")


@router.put("/career-roles/{item_id}", response_model=ApiResponse[CareerRoleRead])
def update_role(item_id: int, payload: CareerRoleWrite, db: DbSession):
    item = save_career_role(db, values=payload, item_id=item_id)
    return ApiResponse(data=item, message="Career role updated")


@router.delete("/career-roles/{item_id}", response_model=ApiResponse[dict[str, bool]])
def delete_role(item_id: int, db: DbSession):
    set_item_active(db, CareerRole, item_id, is_active=False)
    return ApiResponse(data={"deleted": True}, message="Career role deleted")


@router.patch(
    "/career-roles/{item_id}/status", response_model=ApiResponse[CareerRoleRead]
)
def set_role_status(item_id: int, payload: CatalogStatusUpdate, db: DbSession):
    item = set_item_active(db, CareerRole, item_id, is_active=payload.is_active)
    return ApiResponse(data=item, message="Career role status updated")


@router.get(
    "/skills",
    response_model=ApiResponse[Page[SkillRead]],
)
def list_admin_skills(
    db: DbSession,
    search: str | None = Query(default=None, max_length=200),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    return ApiResponse(
        data=paginate_skills(
            db,
            search=search,
            is_active=is_active,
            page=page,
            page_size=page_size,
        ),
        message="Skills retrieved",
    )


@router.post(
    "/skills",
    response_model=ApiResponse[SkillRead],
    status_code=status.HTTP_201_CREATED,
)
def create_skill(payload: SkillWrite, db: DbSession):
    item = create_item(db, Skill, payload.model_dump())
    return ApiResponse(data=item, message="Skill created")


@router.put("/skills/{item_id}", response_model=ApiResponse[SkillRead])
def update_skill(item_id: int, payload: SkillWrite, db: DbSession):
    item = update_item(db, Skill, item_id, payload.model_dump())
    return ApiResponse(data=item, message="Skill updated")


@router.delete("/skills/{item_id}", response_model=ApiResponse[dict[str, bool]])
def delete_skill(item_id: int, db: DbSession):
    set_item_active(db, Skill, item_id, is_active=False)
    return ApiResponse(data={"deleted": True}, message="Skill deleted")


@router.patch("/skills/{item_id}/status", response_model=ApiResponse[SkillRead])
def set_skill_status(item_id: int, payload: CatalogStatusUpdate, db: DbSession):
    item = set_item_active(db, Skill, item_id, is_active=payload.is_active)
    return ApiResponse(data=item, message="Skill status updated")


@router.get(
    "/resources",
    response_model=ApiResponse[Page[LearningResourceRead]],
)
def list_admin_resources(
    db: DbSession,
    search: str | None = Query(default=None, max_length=200),
    resource_type: ResourceType | None = Query(default=None),
    approval_status: Literal["pending", "approved", "rejected"] | None = Query(
        default=None
    ),
    is_active: bool | None = Query(default=None),
    skill_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    return ApiResponse(
        data=paginate_resources(
            db,
            search=search,
            resource_type=resource_type,
            approval_status=approval_status,
            is_active=is_active,
            skill_id=skill_id,
            page=page,
            page_size=page_size,
        ),
        message="Learning resources retrieved",
    )


@router.get(
    "/resources/{item_id}",
    response_model=ApiResponse[AdminLearningResourceDetailRead],
)
def get_admin_resource_detail(item_id: int, db: DbSession):
    return ApiResponse(
        data=get_resource_detail(db, item_id),
        message="Learning resource retrieved",
    )


@router.post(
    "/resources",
    response_model=ApiResponse[LearningResourceRead],
    status_code=status.HTTP_201_CREATED,
)
def create_resource(payload: LearningResourceWrite, db: DbSession):
    item = create_item(db, LearningResource, payload.model_dump())
    return ApiResponse(
        data=serialize_learning_resource(item), message="Learning resource created"
    )


@router.put("/resources/{item_id}", response_model=ApiResponse[LearningResourceRead])
def update_resource(item_id: int, payload: LearningResourceWrite, db: DbSession):
    item = update_learning_resource(
        db, resource_id=item_id, values=payload.model_dump()
    )
    return ApiResponse(
        data=serialize_learning_resource(item), message="Learning resource updated"
    )


@router.patch(
    "/resources/{item_id}/approval",
    response_model=ApiResponse[LearningResourceRead],
)
def update_resource_approval(
    item_id: int, payload: LearningResourceReviewRequest, db: DbSession
):
    item = review_resource(
        db, resource_id=item_id, approval_status=payload.approval_status
    )
    return ApiResponse(
        data=serialize_learning_resource(item), message="Learning resource reviewed"
    )


@router.delete(
    "/resources/{item_id}", response_model=ApiResponse[dict[str, bool]]
)
def delete_resource(item_id: int, db: DbSession):
    set_item_active(db, LearningResource, item_id, is_active=False)
    return ApiResponse(data={"deleted": True}, message="Learning resource deleted")


@router.patch(
    "/resources/{item_id}/status",
    response_model=ApiResponse[LearningResourceRead],
)
def set_resource_status(
    item_id: int, payload: CatalogStatusUpdate, db: DbSession
):
    item = set_item_active(db, LearningResource, item_id, is_active=payload.is_active)
    return ApiResponse(data=item, message="Learning resource status updated")
