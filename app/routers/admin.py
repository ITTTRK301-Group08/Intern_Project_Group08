from fastapi import APIRouter, Depends, status

from app.core.deps import DbSession, require_admin
from app.models.career import CareerCategory, CareerRole, Skill
from app.models.learning_resource import LearningResource
from app.schemas.auth import ApiResponse
from app.schemas.catalog import (
    CareerRoleRead,
    CareerRoleWrite,
    CategoryRead,
    CategoryWrite,
    LearningResourceRead,
    LearningResourceWrite,
    SkillRead,
    SkillWrite,
)
from app.services.catalog_service import (
    create_item,
    delete_item,
    list_categories,
    list_resources,
    list_roles,
    list_skills,
    save_career_role,
    update_item,
)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/catalog")
def get_admin_catalog(db: DbSession):
    return {
        "categories": [
            CategoryRead.model_validate(item) for item in list_categories(db)
        ],
        "roles": [
            CareerRoleRead.model_validate(item)
            for item in list_roles(db, include_inactive=True)
        ],
        "skills": [SkillRead.model_validate(item) for item in list_skills(db)],
        "resources": [
            LearningResourceRead.model_validate(item)
            for item in list_resources(db, include_inactive=True, limit=200)
        ],
    }


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


@router.delete("/career-categories/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(item_id: int, db: DbSession):
    delete_item(db, CareerCategory, item_id)


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


@router.delete("/career-roles/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(item_id: int, db: DbSession):
    delete_item(db, CareerRole, item_id)


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


@router.delete("/skills/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(item_id: int, db: DbSession):
    delete_item(db, Skill, item_id)


@router.post(
    "/resources",
    response_model=ApiResponse[LearningResourceRead],
    status_code=status.HTTP_201_CREATED,
)
def create_resource(payload: LearningResourceWrite, db: DbSession):
    item = create_item(db, LearningResource, payload.model_dump())
    return ApiResponse(data=item, message="Learning resource created")


@router.put("/resources/{item_id}", response_model=ApiResponse[LearningResourceRead])
def update_resource(item_id: int, payload: LearningResourceWrite, db: DbSession):
    item = update_item(db, LearningResource, item_id, payload.model_dump())
    return ApiResponse(data=item, message="Learning resource updated")


@router.delete("/resources/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(item_id: int, db: DbSession):
    delete_item(db, LearningResource, item_id)
