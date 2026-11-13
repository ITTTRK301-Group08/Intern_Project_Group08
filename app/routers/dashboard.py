from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    InterviewHistoryResponse,
    LearningProgressResponse,
    SkillRadarResponse,
)
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: CurrentUser,
    db: DbSession,
) -> DashboardSummaryResponse:
    """Bảng điều khiển tổng hợp: Điểm sẵn sàng nghề nghiệp, vị trí mục tiêu, tổng quan học tập và phỏng vấn."""
    data = dashboard_service.get_dashboard_summary(db, user_id=current_user.id)
    return DashboardSummaryResponse(
        data=data,
        message="Lấy tổng quan bảng điều khiển thành công",
    )


@router.get("/skill-radar", response_model=SkillRadarResponse)
def get_skill_radar(
    current_user: CurrentUser,
    db: DbSession,
    analysis_id: int | None = Query(default=None, description="ID phân tích tùy chọn; mặc định lấy phân tích mới nhất"),
) -> SkillRadarResponse:
    """Dữ liệu biểu đồ Radar kỹ năng: Trình độ hiện tại vs Chuẩn yêu cầu theo vị trí nghề nghiệp."""
    data = dashboard_service.get_skill_radar_data(
        db,
        user_id=current_user.id,
        analysis_id=analysis_id,
    )
    return SkillRadarResponse(
        data=data,
        message="Lấy dữ liệu biểu đồ Radar kỹ năng thành công",
    )


@router.get("/learning-progress", response_model=LearningProgressResponse)
def get_learning_progress(
    current_user: CurrentUser,
    db: DbSession,
) -> LearningProgressResponse:
    """Tiến độ thực hiện lộ trình 30 ngày theo từng tuần (Tuần 1 - Tuần 4)."""
    data = dashboard_service.get_learning_progress(db, user_id=current_user.id)
    return LearningProgressResponse(
        data=data,
        message="Lấy tiến độ học tập thành công",
    )


@router.get("/interview-history", response_model=InterviewHistoryResponse)
def get_interview_history(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> InterviewHistoryResponse:
    """Lịch sử các phiên phỏng vấn thử của người dùng."""
    data = dashboard_service.get_interview_history(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return InterviewHistoryResponse(
        data=data,
        message="Lấy lịch sử phỏng vấn thành công",
    )
