from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.learning_plan import (
    LearningPlanApiResponse,
    LearningPlanCreateRequest,
    LearningPlanItemApiResponse,
    LearningPlanItemUpdateRequest,
    LearningPlanListApiResponse,
    LearningPlanStatusUpdateRequest,
)
from app.services import learning_plan_service

router = APIRouter(prefix="/api/v1/learning-plans", tags=["learning-plans"])


@router.post("", response_model=LearningPlanApiResponse, status_code=status.HTTP_201_CREATED)
def create_learning_plan(
    payload: LearningPlanCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> LearningPlanApiResponse:
    """Tạo lộ trình học tập cá nhân hóa 30 ngày từ báo cáo phân tích đã hoàn thành (UC-08)."""
    data = learning_plan_service.create_plan_from_analysis(
        db,
        user_id=current_user.id,
        analysis_id=payload.analysis_id,
        title=payload.title,
        duration_days=payload.duration_days,
    )
    return LearningPlanApiResponse(
        data=data,
        message="Tạo lộ trình học tập cá nhân hóa 30 ngày thành công",
    )


@router.get("", response_model=LearningPlanListApiResponse)
def list_learning_plans(
    current_user: CurrentUser,
    db: DbSession,
    include_archived: bool = True,
) -> LearningPlanListApiResponse:
    """Lấy danh sách các lộ trình học tập của người dùng hiện tại."""
    data = learning_plan_service.get_user_plans(
        db,
        user_id=current_user.id,
        include_archived=include_archived,
    )
    return LearningPlanListApiResponse(
        data=data,
        message="Lấy danh sách lộ trình học tập thành công",
    )


@router.get("/{plan_id}", response_model=LearningPlanApiResponse)
def get_learning_plan_detail(
    plan_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> LearningPlanApiResponse:
    """Lấy chi tiết lộ trình học tập và danh sách nhiệm vụ 4 tuần kèm tài nguyên."""
    data = learning_plan_service.get_plan_detail(
        db,
        user_id=current_user.id,
        plan_id=plan_id,
    )
    return LearningPlanApiResponse(
        data=data,
        message="Lấy chi tiết lộ trình học tập thành công",
    )


@router.patch("/{plan_id}/status", response_model=LearningPlanApiResponse)
def update_learning_plan_status(
    plan_id: int,
    payload: LearningPlanStatusUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> LearningPlanApiResponse:
    """Cập nhật trạng thái lộ trình học tập: active, completed, archived."""
    data = learning_plan_service.update_plan_status(
        db,
        user_id=current_user.id,
        plan_id=plan_id,
        new_status=payload.status,
    )
    return LearningPlanApiResponse(
        data=data,
        message="Cập nhật trạng thái lộ trình thành công",
    )


@router.patch("/{plan_id}/items/{item_id}", response_model=LearningPlanItemApiResponse)
def update_learning_plan_item_completion(
    plan_id: int,
    item_id: int,
    payload: LearningPlanItemUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> LearningPlanItemApiResponse:
    """Đánh dấu hoàn thành hoặc bỏ hoàn thành một nhiệm vụ trong lộ trình."""
    data = learning_plan_service.update_plan_item(
        db,
        user_id=current_user.id,
        plan_id=plan_id,
        item_id=item_id,
        is_completed=payload.is_completed,
    )
    return LearningPlanItemApiResponse(
        data=data,
        message="Cập nhật trạng thái nhiệm vụ học tập thành công",
    )
