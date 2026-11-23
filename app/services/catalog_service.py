from collections.abc import Sequence
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.career import CareerCategory, CareerRole, Skill
from app.models.learning_resource import LearningResource
from app.models.profile_data import CareerRoleSkill
from app.schemas.catalog import (
    CareerRoleRead,
    CareerRoleWrite,
    CategoryRead,
    LearningResourceRead,
    SkillRead,
)

ModelT = TypeVar("ModelT", CareerCategory, CareerRole, Skill, LearningResource)
ActiveCatalogModelT = TypeVar("ActiveCatalogModelT", CareerRole, Skill, LearningResource)


def list_categories(db: Session) -> Sequence[CareerCategory]:
    return db.scalars(
        select(CareerCategory).order_by(CareerCategory.name)
    ).all()


def list_roles(
    db: Session,
    *,
    category_id: int | None = None,
    level: str | None = None,
    include_inactive: bool = False,
) -> Sequence[CareerRole]:
    required_skills = CareerRole.required_skills
    if not include_inactive:
        required_skills = required_skills.and_(
            CareerRoleSkill.skill.has(Skill.is_active.is_(True))
        )
    query = select(CareerRole).options(
        joinedload(CareerRole.category),
        joinedload(required_skills).joinedload(CareerRoleSkill.skill),
    )
    if category_id is not None:
        query = query.where(CareerRole.category_id == category_id)
    if level is not None and level.strip():
        query = query.where(func.lower(CareerRole.level) == level.strip().lower())
    if not include_inactive:
        query = query.where(CareerRole.is_active.is_(True))
        query = query.execution_options(populate_existing=True)
    return db.scalars(query.order_by(CareerRole.name, CareerRole.level)).unique().all()


def get_role_by_id(
    db: Session, role_id: int, *, include_inactive: bool = False
) -> CareerRole:
    required_skills = CareerRole.required_skills
    if not include_inactive:
        required_skills = required_skills.and_(
            CareerRoleSkill.skill.has(Skill.is_active.is_(True))
        )
    query = (
        select(CareerRole)
        .options(
            joinedload(CareerRole.category),
            joinedload(required_skills).joinedload(CareerRoleSkill.skill),
        )
        .where(CareerRole.id == role_id)
    )
    if not include_inactive:
        query = query.where(CareerRole.is_active.is_(True))
        query = query.execution_options(populate_existing=True)
    role = db.scalars(query).unique().one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career role not found",
        )
    return role


def get_role_skills(
    db: Session, role_id: int, *, include_inactive: bool = False
) -> list[CareerRoleSkill]:
    role = get_role_by_id(db, role_id, include_inactive=include_inactive)
    return sorted(
        (
            item
            for item in role.required_skills
            if include_inactive or item.skill.is_active
        ),
        key=lambda item: (-float(item.weight), -item.required_level, item.skill_id),
    )


def list_skills(
    db: Session,
    *,
    search: str | None = None,
    category_id: int | None = None,
    role_id: int | None = None,
    include_inactive: bool = False,
) -> Sequence[Skill]:
    query = select(Skill)

    if category_id is not None:
        role_subquery = (
            select(CareerRoleSkill.skill_id)
            .join(CareerRole, CareerRole.id == CareerRoleSkill.career_role_id)
            .where(
                CareerRole.category_id == category_id,
                CareerRole.is_active.is_(True),
            )
        )
        query = query.where(Skill.id.in_(role_subquery))

    if role_id is not None:
        role_subquery = (
            select(CareerRoleSkill.skill_id)
            .join(CareerRole, CareerRole.id == CareerRoleSkill.career_role_id)
            .where(
                CareerRoleSkill.career_role_id == role_id,
                CareerRole.is_active.is_(True),
            )
        )
        query = query.where(Skill.id.in_(role_subquery))

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            Skill.name.ilike(term) | Skill.description.ilike(term)
        )

    if not include_inactive:
        query = query.where(Skill.is_active.is_(True))

    return db.scalars(query.order_by(Skill.name).distinct()).all()


def list_resources(
    db: Session,
    *,
    skill_id: int | None = None,
    role_id: int | None = None,
    search: str | None = None,
    resource_type: str | None = None,
    include_inactive: bool = False,
    include_unapproved: bool = False,
    limit: int = 100,
) -> Sequence[LearningResource]:
    query = select(LearningResource).options(
        joinedload(LearningResource.skill)
        .selectinload(Skill.career_roles)
        .joinedload(CareerRoleSkill.career_role)
    )
    if skill_id is not None:
        query = query.where(LearningResource.skill_id == skill_id)
    if role_id is not None:
        role_skill_ids = (
            select(CareerRoleSkill.skill_id)
            .join(CareerRole, CareerRole.id == CareerRoleSkill.career_role_id)
            .where(
                CareerRole.id == role_id,
                CareerRole.is_active.is_(True),
            )
        )
        query = query.where(LearningResource.skill_id.in_(role_skill_ids))
    if resource_type:
        query = query.where(LearningResource.resource_type == resource_type)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            LearningResource.title.ilike(term)
            | LearningResource.provider.ilike(term)
            | LearningResource.description.ilike(term)
        )
    if not include_inactive:
        query = query.where(LearningResource.is_active.is_(True))
    if not include_unapproved:
        query = query.where(LearningResource.approval_status == "approved")
    return db.scalars(
        query.order_by(LearningResource.title).limit(limit)
    ).all()


def serialize_learning_resource(resource: LearningResource) -> dict:
    data = LearningResourceRead.model_validate(resource).model_dump()
    data["related_roles"] = [
        {"id": role.id, "name": role.name, "level": role.level}
        for role_link in (resource.skill.career_roles if resource.skill else [])
        if (role := role_link.career_role) is not None and role.is_active
    ]
    return data


def get_approved_resource(db: Session, resource_id: int) -> LearningResource:
    resource = db.scalar(
        select(LearningResource)
        .options(
            joinedload(LearningResource.skill)
            .selectinload(Skill.career_roles)
            .joinedload(CareerRoleSkill.career_role)
        )
        .where(
            LearningResource.id == resource_id,
            LearningResource.is_active.is_(True),
            LearningResource.approval_status == "approved",
        )
    )
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning resource not found",
        )
    return resource


def review_resource(
    db: Session, *, resource_id: int, approval_status: str
) -> LearningResource:
    resource = db.get(LearningResource, resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning resource not found",
        )
    resource.approval_status = approval_status
    _commit(db, "review learning resource")
    db.refresh(resource)
    return resource


def update_learning_resource(
    db: Session, *, resource_id: int, values: dict
) -> LearningResource:
    resource = db.get(LearningResource, resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning resource not found",
        )
    for key, value in values.items():
        setattr(resource, key, value)
    resource.approval_status = "pending"
    _commit(db, "update learning resource")
    db.refresh(resource)
    return resource


def _commit(db: Session, operation: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot {operation}: a unique or foreign-key constraint was violated",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while updating catalog",
        ) from exc


def create_item(db: Session, model: type[ModelT], values: dict) -> ModelT:
    item = model(**values)
    db.add(item)
    _commit(db, "create catalog item")
    db.refresh(item)
    return item


def update_item(
    db: Session, model: type[ModelT], item_id: int, values: dict
) -> ModelT:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")
    for key, value in values.items():
        setattr(item, key, value)
    _commit(db, "update catalog item")
    db.refresh(item)
    return item


def delete_item(db: Session, model: type[ModelT], item_id: int) -> None:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found")
    db.delete(item)
    _commit(db, "delete catalog item")


def set_item_active(
    db: Session,
    model: type[ActiveCatalogModelT],
    item_id: int,
    *,
    is_active: bool,
) -> ActiveCatalogModelT:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Catalog item not found"
        )
    item.is_active = is_active
    _commit(db, "update catalog item status")
    db.refresh(item)
    return item


def save_career_role(
    db: Session, *, values: CareerRoleWrite, item_id: int | None = None
) -> CareerRole:
    role = db.get(CareerRole, item_id) if item_id is not None else CareerRole()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career role not found")

    for field in ("category_id", "name", "slug", "level", "description", "is_active"):
        setattr(role, field, getattr(values, field))

    skill_ids = [item.skill_id for item in values.required_skills]
    skills_by_id = {
        skill.id: skill
        for skill in db.scalars(select(Skill).where(Skill.id.in_(skill_ids))).all()
    } if skill_ids else {}
    missing_ids = set(skill_ids) - set(skills_by_id)
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown skill ids: {sorted(missing_ids)}",
        )

    role.required_skills = [
        CareerRoleSkill(
            skill=skills_by_id[item.skill_id],
            required_level=item.required_level,
            is_required=item.is_required,
            weight=item.weight,
        )
        for item in values.required_skills
    ]
    db.add(role)
    _commit(db, "save career role")
    saved_role = db.scalars(
        select(CareerRole)
        .options(
            joinedload(CareerRole.category),
            joinedload(CareerRole.required_skills).joinedload(CareerRoleSkill.skill),
        )
        .where(CareerRole.id == role.id)
    ).unique().one_or_none()
    if saved_role is None:
        raise RuntimeError("Career role disappeared after saving")
    return saved_role


def bootstrap_admin(db: Session, *, email: str, password: str):
    from app.core.security import hash_password
    from app.models.user import User

    normalized_email = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        if existing.role != "admin":
            raise ValueError(
                f"Account {normalized_email} already exists and is not an admin; "
                "refusing to elevate it automatically."
            )
        return existing, False

    admin = User(
        email=normalized_email,
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(User).where(User.email == normalized_email))
        if existing is not None and existing.role == "admin":
            return existing, False
        raise
    db.refresh(admin)
    return admin, True


def _page_meta(total: int, page: int, page_size: int) -> dict[str, int]:
    total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def paginate_categories(
    db: Session,
    *,
    search: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            CareerCategory.name.ilike(term)
            | CareerCategory.slug.ilike(term)
            | CareerCategory.description.ilike(term)
        )

    total_query = select(func.count(CareerCategory.id))
    if conditions:
        total_query = total_query.where(*conditions)
    total = db.scalar(total_query) or 0

    query = select(CareerCategory).order_by(CareerCategory.name)
    if conditions:
        query = query.where(*conditions)
    categories = db.scalars(
        query.offset(max(0, (page - 1) * page_size)).limit(page_size)
    ).all()
    return {
        "items": [CategoryRead.model_validate(item) for item in categories],
        **_page_meta(total, page, page_size),
    }


def get_category_detail(db: Session, category_id: int) -> dict:
    category = db.get(CareerCategory, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career category not found",
        )
    roles = db.scalars(
        select(CareerRole)
        .where(CareerRole.category_id == category_id)
        .order_by(CareerRole.name, CareerRole.level)
    ).all()
    data = CategoryRead.model_validate(category).model_dump()
    data["roles"] = [
        {
            "id": role.id,
            "name": role.name,
            "level": role.level,
            "is_active": role.is_active,
        }
        for role in roles
    ]
    data["role_count"] = len(roles)
    return data


def ensure_category_deletable(db: Session, category_id: int) -> None:
    role_count = (
        db.scalar(
            select(func.count(CareerRole.id)).where(
                CareerRole.category_id == category_id
            )
        )
        or 0
    )
    if role_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot delete career category: "
                f"{role_count} career role(s) still reference it"
            ),
        )


def paginate_roles(
    db: Session,
    *,
    search: str | None = None,
    category_id: int | None = None,
    level: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            CareerRole.name.ilike(term)
            | CareerRole.slug.ilike(term)
            | CareerRole.description.ilike(term)
        )
    if category_id is not None:
        conditions.append(CareerRole.category_id == category_id)
    if level is not None and level.strip():
        conditions.append(func.lower(CareerRole.level) == level.strip().lower())
    if is_active is not None:
        conditions.append(CareerRole.is_active.is_(is_active))

    total_query = select(func.count(CareerRole.id))
    if conditions:
        total_query = total_query.where(*conditions)
    total = db.scalar(total_query) or 0

    query = select(CareerRole).options(
        joinedload(CareerRole.category),
        joinedload(CareerRole.required_skills).joinedload(CareerRoleSkill.skill),
    )
    if conditions:
        query = query.where(*conditions)
    roles = (
        db.scalars(
            query.order_by(CareerRole.name, CareerRole.level)
            .offset(max(0, (page - 1) * page_size))
            .limit(page_size)
        )
        .unique()
        .all()
    )
    return {
        "items": [CareerRoleRead.model_validate(item) for item in roles],
        **_page_meta(total, page, page_size),
    }


def paginate_skills(
    db: Session,
    *,
    search: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            Skill.name.ilike(term) | Skill.description.ilike(term)
        )
    if is_active is not None:
        conditions.append(Skill.is_active.is_(is_active))

    total_query = select(func.count(Skill.id))
    if conditions:
        total_query = total_query.where(*conditions)
    total = db.scalar(total_query) or 0

    query = select(Skill).order_by(Skill.name)
    if conditions:
        query = query.where(*conditions)
    skills = db.scalars(
        query.offset(max(0, (page - 1) * page_size)).limit(page_size)
    ).all()
    return {
        "items": [SkillRead.model_validate(item) for item in skills],
        **_page_meta(total, page, page_size),
    }


def paginate_resources(
    db: Session,
    *,
    search: str | None = None,
    resource_type: str | None = None,
    approval_status: str | None = None,
    is_active: bool | None = None,
    skill_id: int | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            LearningResource.title.ilike(term)
            | LearningResource.provider.ilike(term)
            | LearningResource.description.ilike(term)
        )
    if resource_type:
        conditions.append(LearningResource.resource_type == resource_type)
    if approval_status:
        conditions.append(LearningResource.approval_status == approval_status)
    if is_active is not None:
        conditions.append(LearningResource.is_active.is_(is_active))
    if skill_id is not None:
        conditions.append(LearningResource.skill_id == skill_id)

    total_query = select(func.count(LearningResource.id))
    if conditions:
        total_query = total_query.where(*conditions)
    total = db.scalar(total_query) or 0

    query = select(LearningResource).options(
        joinedload(LearningResource.skill)
        .selectinload(Skill.career_roles)
        .joinedload(CareerRoleSkill.career_role)
    )
    if conditions:
        query = query.where(*conditions)
    resources = db.scalars(
        query.order_by(LearningResource.title)
        .offset(max(0, (page - 1) * page_size))
        .limit(page_size)
    ).all()
    return {
        "items": [serialize_learning_resource(item) for item in resources],
        **_page_meta(total, page, page_size),
    }


def get_resource_detail(db: Session, resource_id: int) -> dict:
    resource = db.scalar(
        select(LearningResource)
        .options(
            joinedload(LearningResource.skill)
            .selectinload(Skill.career_roles)
            .joinedload(CareerRoleSkill.career_role)
            .joinedload(CareerRole.category)
        )
        .where(LearningResource.id == resource_id)
    )
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning resource not found",
        )

    data = serialize_learning_resource(resource)
    related_categories: dict[int, dict[str, int | str]] = {}
    for role_link in resource.skill.career_roles if resource.skill else []:
        role = role_link.career_role
        if role is None or not role.is_active or role.category is None:
            continue
        related_categories[role.category.id] = {
            "id": role.category.id,
            "name": role.category.name,
        }
    data["related_categories"] = list(related_categories.values())
    return data
