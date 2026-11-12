"""Router nghiệp vụ phân tích khoảng cách kỹ năng (M4)."""

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.analysis import (
    AnalysisDetailRead,
    AnalysisDetailResponse,
    AnalysisHistoryData,
    AnalysisHistoryResponse,
    AnalysisRead,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSkillGapRead,
    AnalysisSkillsData,
    AnalysisSkillsResponse,
    AnalysisStatusRead,
    AnalysisStatusResponse,
)
from app.schemas.auth import ApiResponse
from app.services.analysis_service import (
    create_analysis,
    get_analysis_for_user,
    list_analyses_for_user,
    list_analysis_skill_gaps,
    run_analysis_pipeline,
)

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis_request(
    payload: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[AnalysisRead]:
    """Tạo yêu cầu phân tích và trả 202 kèm ``analysis_id``.

    Consent, quyền sở hữu CV và vị trí mục tiêu được kiểm tra đồng bộ trước
    khi tạo báo cáo. Tác vụ AI chạy nền và cập nhật trạng thái sau đó.
    `user_id` chỉ lấy từ JWT hiện tại.
    """
    analysis = create_analysis(
        db,
        user_id=current_user.id,
        cv_id=payload.cv_id,
        career_role_id=payload.career_role_id,
        consent=payload.ai_consent,
    )
    background_tasks.add_task(run_analysis_pipeline, analysis.id)
    return ApiResponse(
        data=AnalysisRead.model_validate(analysis),
        message="Đã tạo yêu cầu phân tích. Hệ thống đang xử lý.",
    )


@router.get("", response_model=AnalysisHistoryResponse)
def list_analyses(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[AnalysisHistoryData]:
    """Lấy lịch sử báo cáo của người dùng hiện tại (mới nhất trước)."""
    analyses, total = list_analyses_for_user(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(
        data=AnalysisHistoryData(
            analyses=[AnalysisRead.model_validate(item) for item in analyses],
            total=total,
        ),
        message="Lấy lịch sử phân tích thành công.",
    )


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
def get_analysis_detail(
    analysis_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[AnalysisDetailRead]:
    """Xem chi tiết báo cáo thuộc người dùng hiện tại."""
    analysis = get_analysis_for_user(
        db,
        analysis_id=analysis_id,
        user_id=current_user.id,
    )
    return ApiResponse(
        data=AnalysisDetailRead.model_validate(analysis),
        message="Lấy chi tiết báo cáo phân tích thành công.",
    )


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(
    analysis_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[AnalysisStatusRead]:
    """Kiểm tra trạng thái xử lý để giao diện polling."""
    analysis = get_analysis_for_user(
        db,
        analysis_id=analysis_id,
        user_id=current_user.id,
    )
    return ApiResponse(
        data=AnalysisStatusRead.model_validate(analysis),
        message="Lấy trạng thái phân tích thành công.",
    )


@router.get("/{analysis_id}/skills", response_model=AnalysisSkillsResponse)
def get_analysis_skills(
    analysis_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[AnalysisSkillsData]:
    """Lấy điểm từng kỹ năng của báo cáo thuộc người dùng hiện tại."""
    gaps = list_analysis_skill_gaps(
        db,
        analysis_id=analysis_id,
        user_id=current_user.id,
    )
    return ApiResponse(
        data=AnalysisSkillsData(
            analysis_id=analysis_id,
            skills=[AnalysisSkillGapRead.model_validate(gap) for gap in gaps],
        ),
        message="Lấy danh sách kỹ năng của báo cáo thành công.",
    )
