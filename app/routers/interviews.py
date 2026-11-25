"""Router cho nghiệp vụ phỏng vấn thử (M6)."""

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import ApiResponse
from app.schemas.interview.request import (
    InterviewAnswerSubmitRequest,
    InterviewCreateRequest,
)
from app.schemas.interview.response import (
    InterviewAnswerRead,
    InterviewAnswerResultRead,
    InterviewAnswerResultResponse,
    InterviewCompletionRead,
    InterviewCompletionResponse,
    InterviewQuestionRead,
    InterviewQuestionsResponse,
    InterviewSessionDetailResponse,
    InterviewSessionListData,
    InterviewSessionListResponse,
    InterviewSessionRead,
    InterviewSessionResponse,
)
from app.services.interview_service import (
    complete_interview_session,
    create_interview_session,
    get_interview_questions,
    get_interview_session_detail,
    list_interview_sessions,
    submit_interview_answer,
)

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


@router.get("", response_model=InterviewSessionListResponse)
def get_interview_sessions(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
) -> InterviewSessionListResponse:
    """Liệt kê phiên phỏng vấn của chính người dùng hiện tại."""
    data = list_interview_sessions(
        db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return InterviewSessionListResponse(
        data=InterviewSessionListData(**data),
        message="Lấy danh sách phiên phỏng vấn thành công.",
    )


@router.get(
    "/{session_id}",
    response_model=InterviewSessionDetailResponse,
)
def get_interview_detail(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> InterviewSessionDetailResponse:
    """Lấy chi tiết một phiên phỏng vấn kèm điểm và feedback từng câu."""
    session = get_interview_session_detail(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    return InterviewSessionDetailResponse(
        data=session,
        message="Lấy chi tiết phiên phỏng vấn thành công.",
    )


@router.get(
    "/{session_id}/questions",
    response_model=InterviewQuestionsResponse,
)
def get_interview_session_questions(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> InterviewQuestionsResponse:
    """Lấy danh sách câu hỏi của phiên theo đúng thứ tự."""
    questions = get_interview_questions(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    return InterviewQuestionsResponse(
        data=questions,
        message="Lấy danh sách câu hỏi phỏng vấn thành công.",
    )


@router.post(
    "/{session_id}/answers",
    response_model=InterviewAnswerResultResponse,
    status_code=201,
)
async def submit_answer(
    session_id: int,
    payload: InterviewAnswerSubmitRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> InterviewAnswerResultResponse:
    """Gửi câu trả lời, gọi AI chấm điểm và lưu kết quả.

    AI chỉ được gọi trong service; router chỉ xử lý HTTP và envelope.
    """
    result = await submit_interview_answer(
        db,
        user_id=current_user.id,
        session_id=session_id,
        question_id=payload.question_id,
        answer_text=payload.answer_text,
    )
    return InterviewAnswerResultResponse(
        data=InterviewAnswerResultRead(
            answer=InterviewAnswerRead.model_validate(result["answer"]),
            session_status=result["session_status"],
            question_count=result["question_count"],
            answered_count=result["answered_count"],
        ),
        message="Gửi câu trả lời và chấm điểm thành công.",
    )


@router.post(
    "/{session_id}/complete",
    response_model=InterviewCompletionResponse,
)
def complete_interview(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> InterviewCompletionResponse:
    """Hoàn thành phiên khi đã trả lời đủ câu hỏi và tính điểm trung bình."""
    result = complete_interview_session(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    return InterviewCompletionResponse(
        data=InterviewCompletionRead(**result),
        message="Hoàn thành phiên phỏng vấn thành công.",
    )
