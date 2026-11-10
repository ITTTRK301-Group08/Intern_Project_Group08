"""Router tạo phiên phỏng vấn thử bằng AI."""

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import ApiResponse
from app.schemas.interview.request import InterviewCreateRequest
from app.schemas.interview.response import InterviewSessionRead
from app.services.interview_service import create_interview_session

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])


@router.post(
    "",
    response_model=ApiResponse[InterviewSessionRead],
    status_code=201,
)
async def create_interview(
    payload: InterviewCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[InterviewSessionRead]:
    """Tạo phiên phỏng vấn và trả về đúng 3 câu hỏi đã lưu.

    `user_id` chỉ được lấy từ JWT hiện tại, không nhận từ request body.
    Router không truy vấn database và không gọi AI trực tiếp.
    """
    session = await create_interview_session(
        db,
        user_id=current_user.id,
        career_role_id=payload.career_role_id,
        consent=payload.ai_consent,
    )
    return ApiResponse(
        data=session,
        message="Tạo phiên phỏng vấn thành công.",
    )
