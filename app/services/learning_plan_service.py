from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.analysis import Analysis
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.schemas.learning_plan import LearningPlanStatus


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Learning plan or item not found",
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while updating learning plan",
        ) from exc


def list_user_learning_plans(db: Session, *, user_id: int) -> list[LearningPlan]:
    return db.scalars(
        select(LearningPlan)
        .options(selectinload(LearningPlan.items))
        .where(LearningPlan.user_id == user_id)
        .order_by(LearningPlan.created_at.desc(), LearningPlan.id.desc())
    ).all()


def get_user_learning_plan(
    db: Session, *, user_id: int, plan_id: int
) -> LearningPlan | None:
    return db.scalar(
        select(LearningPlan)
        .options(
            selectinload(LearningPlan.items).joinedload(LearningPlanItem.resource)
        )
        .where(LearningPlan.id == plan_id, LearningPlan.user_id == user_id)
    )


def update_user_learning_plan_status(
    db: Session,
    *,
    user_id: int,
    plan_id: int,
    new_status: LearningPlanStatus,
) -> LearningPlan:
    plan = db.scalar(
        select(LearningPlan)
        .where(LearningPlan.id == plan_id, LearningPlan.user_id == user_id)
        .with_for_update()
    )
    if plan is None:
        raise _not_found()

    if new_status == "active":
        analysis = db.scalar(
            select(Analysis)
            .where(Analysis.id == plan.analysis_id, Analysis.user_id == user_id)
            .with_for_update()
        )
        if analysis is None:
            raise _not_found()
        active_plan = db.scalar(
            select(LearningPlan.id).where(
                LearningPlan.analysis_id == plan.analysis_id,
                LearningPlan.status == "active",
                LearningPlan.id != plan_id,
            )
        )
        if active_plan is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another active learning plan already exists for this analysis",
            )
    plan.status = new_status
    plan.status = new_status
    _commit(db)
    db.refresh(plan)
    return plan


def update_user_learning_plan_item(
    db: Session,
    *,
    user_id: int,
    plan_id: int,
    item_id: int,
    is_completed: bool,
) -> LearningPlanItem:
    item = db.scalar(
        select(LearningPlanItem)
        .join(LearningPlan, LearningPlan.id == LearningPlanItem.plan_id)
        .join(Analysis, Analysis.id == LearningPlan.analysis_id)
        .where(
            LearningPlan.id == plan_id,
            LearningPlanItem.id == item_id,
            LearningPlan.user_id == user_id,
            Analysis.user_id == user_id,
        )
        .with_for_update()
    )
    if item is None:
        raise _not_found()

    item.is_completed = is_completed
    item.completed_at = (
        datetime.now(timezone.utc).replace(tzinfo=None) if is_completed else None
    )
    _commit(db)
    db.refresh(item)
    return item
