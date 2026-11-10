from collections.abc import Sequence
from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.career import CareerCategory, CareerRole, Skill
from app.models.learning_resource import LearningResource
from app.models.profile_data import CareerRoleSkill
from app.schemas.catalog import CareerRoleWrite

ModelT = TypeVar("ModelT", CareerCategory, CareerRole, Skill, LearningResource)


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
    query = select(CareerRole).options(
        joinedload(CareerRole.category),
        joinedload(CareerRole.required_skills).joinedload(CareerRoleSkill.skill),
    )
    if category_id is not None:
        query = query.where(CareerRole.category_id == category_id)
    if level is not None and level.strip():
        query = query.where(func.lower(CareerRole.level) == level.strip().lower())
    if not include_inactive:
        query = query.where(CareerRole.is_active.is_(True))
    return db.scalars(query.order_by(CareerRole.name, CareerRole.level)).unique().all()


def get_role_by_id(
    db: Session, role_id: int, *, include_inactive: bool = False
) -> CareerRole:
    query = (
        select(CareerRole)
        .options(
            joinedload(CareerRole.category),
            joinedload(CareerRole.required_skills).joinedload(CareerRoleSkill.skill),
        )
        .where(CareerRole.id == role_id)
    )
    if not include_inactive:
        query = query.where(CareerRole.is_active.is_(True))
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
        role.required_skills,
        key=lambda item: (-float(item.weight), -item.required_level, item.skill_id),
    )


def list_skills(
    db: Session, *, search: str | None = None
) -> Sequence[Skill]:
    query = select(Skill)
    if search:
        query = query.where(Skill.name.ilike(f"%{search.strip()}%"))
    return db.scalars(query.order_by(Skill.name)).all()


def list_resources(
    db: Session,
    *,
    skill_id: int | None = None,
    search: str | None = None,
    include_inactive: bool = False,
    limit: int = 100,
) -> Sequence[LearningResource]:
    query = select(LearningResource).options(joinedload(LearningResource.skill))
    if skill_id is not None:
        query = query.where(LearningResource.skill_id == skill_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            LearningResource.title.ilike(term)
            | LearningResource.provider.ilike(term)
            | LearningResource.description.ilike(term)
        )
    if not include_inactive:
        query = query.where(LearningResource.is_active.is_(True))
    return db.scalars(
        query.order_by(LearningResource.title).limit(limit)
    ).all()


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
