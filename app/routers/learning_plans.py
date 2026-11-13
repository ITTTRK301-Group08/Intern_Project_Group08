from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DbSession
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.schemas.learning_plan import (
    LearningPlanItemRead,
    LearningPlanItemResponse,
    LearningPlanItemUpdate,
    LearningPlanListItem,
    LearningPlanListResponse,
    LearningPlanRead,
    LearningPlanResponse,
    LearningPlanStatusData,
    LearningPlanStatusResponse,
    LearningPlanStatusUpdate,
)
from app.services.learning_plan_service import (
    get_user_learning_plan,
    list_user_learning_plans,
    update_user_learning_plan_item,
    update_user_learning_plan_status,
)

router = APIRouter(prefix="/api/v1/learning-plans", tags=["learning plans"])


def _item_read(item: LearningPlanItem) -> LearningPlanItemRead:
    return LearningPlanItemRead(
        id=item.id,
        skill_id=item.skill_id,
        week_number=item.week_number,
        task_description=item.task_description,
        estimated_hours=item.estimated_hours,
        is_completed=item.is_completed,
        completed_at=item.completed_at,
        resource_id=item.resource_id,
        resource_title=item.resource.title if item.resource else None,
        resource_url=item.resource.url if item.resource else None,
    )


def _plan_read(plan: LearningPlan) -> LearningPlanRead:
    return LearningPlanRead(
        id=plan.id,
        title=plan.title,
        analysis_id=plan.analysis_id,
        status=plan.status,
        start_date=plan.start_date,
        end_date=plan.end_date,
        created_at=plan.created_at,
        items=[_item_read(item) for item in plan.items],
    )


@router.get("", response_model=LearningPlanListResponse)
def list_learning_plans(
    current_user: CurrentUser, db: DbSession
) -> LearningPlanListResponse:
    plans = list_user_learning_plans(db, user_id=current_user.id)
    return LearningPlanListResponse(
        data=[
            LearningPlanListItem(
                id=plan.id,
                title=plan.title,
                analysis_id=plan.analysis_id,
                status=plan.status,
                start_date=plan.start_date,
                end_date=plan.end_date,
                created_at=plan.created_at,
                item_count=len(plan.items),
                completed_item_count=sum(item.is_completed for item in plan.items),
            )
            for plan in plans
        ],
        message="Learning plans retrieved",
    )


@router.get("/{plan_id}", response_model=LearningPlanResponse)
def get_learning_plan(
    plan_id: int, current_user: CurrentUser, db: DbSession
) -> LearningPlanResponse:
    plan = get_user_learning_plan(db, user_id=current_user.id, plan_id=plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Learning plan not found"
        )
    return LearningPlanResponse(
        data=_plan_read(plan), message="Learning plan retrieved"
    )


@router.patch("/{plan_id}/items/{item_id}", response_model=LearningPlanItemResponse)
def update_learning_plan_item(
    plan_id: int,
    item_id: int,
    payload: LearningPlanItemUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> LearningPlanItemResponse:
    item = update_user_learning_plan_item(
        db,
        user_id=current_user.id,
        plan_id=plan_id,
        item_id=item_id,
        is_completed=payload.is_completed,
    )
    db.refresh(item, attribute_names=["resource"])
    return LearningPlanItemResponse(
        data=_item_read(item), message="Learning plan item updated"
    )


@router.patch("/{plan_id}/status", response_model=LearningPlanStatusResponse)
def update_learning_plan_status(
    plan_id: int,
    payload: LearningPlanStatusUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> LearningPlanStatusResponse:
    plan = update_user_learning_plan_status(
        db,
        user_id=current_user.id,
        plan_id=plan_id,
        new_status=payload.status,
    )
    return LearningPlanStatusResponse(
        data=LearningPlanStatusData(id=plan.id, status=plan.status),
        message="Learning plan status updated",
    )
