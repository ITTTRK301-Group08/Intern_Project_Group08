"""Router nghiệp vụ phỏng vấn thử (M6).

Cung cấp luồng tuần tự: tạo phiên với đúng 3 câu hỏi, xem câu hỏi,
gửi và chấm điểm từng câu trả lời, hoàn thành phiên, cùng lịch sử/chi tiết.
Mọi endpoint đều yêu cầu JWT và chỉ thao tác trên dữ liệu của chính người dùng.
"""

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import ApiResponse
from app.schemas.interview import (
    InterviewAnswerCreateRequest,
    InterviewAnswerRead,
    InterviewAnswerResponse,
    InterviewCreateRequest,
    InterviewHistoryData,
    InterviewHistoryResponse,
    InterviewQuestionRead,
    InterviewQuestionsData,
    InterviewQuestionsResponse,
    InterviewSessionRead,
    InterviewSessionResponse,
    InterviewSummaryRead,
)
from app.services.interview_service import (
    complete_interview_session,
    create_interview_session,
    get_session_for_user,
    get_session_questions,
    list_sessions_for_user,
    submit_interview_answer,
)

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])


@router.post(
    "",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
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


@router.get("", response_model=InterviewHistoryResponse)
def list_interviews(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[InterviewHistoryData]:
    """Lấy lịch sử phiên phỏng vấn của người dùng hiện tại (mới nhất trước)."""
    sessions, total = list_sessions_for_user(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return ApiResponse(
        data=InterviewHistoryData(
            interviews=[
                InterviewSummaryRead.model_validate(item) for item in sessions
            ],
            total=total,
        ),
        message="Lấy lịch sử phỏng vấn thành công.",
    )


@router.get("/{session_id}", response_model=InterviewSessionResponse)
def get_interview_detail(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[InterviewSessionRead]:
    """Xem chi tiết một phiên phỏng vấn thuộc người dùng hiện tại."""
    session = get_session_for_user(
        db,
        session_id=session_id,
        user_id=current_user.id,
    )
    return ApiResponse(
        data=InterviewSessionRead.model_validate(session),
        message="Lấy chi tiết phiên phỏng vấn thành công.",
    )


@router.get("/{session_id}/questions", response_model=InterviewQuestionsResponse)
def get_interview_questions(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[InterviewQuestionsData]:
    """Lấy danh sách câu hỏi theo thứ tự của một phiên."""
    session = get_session_questions(
        db,
        session_id=session_id,
        user_id=current_user.id,
    )
    return ApiResponse(
        data=InterviewQuestionsData(
            session_id=session.id,
            questions=[
                InterviewQuestionRead.model_validate(item)
                for item in session.questions
            ],
        ),
        message="Lấy danh sách câu hỏi phỏng vấn thành công.",
    )


@router.post(
    "/{session_id}/answers",
    response_model=InterviewAnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_answer(
    session_id: int,
    payload: InterviewAnswerCreateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[InterviewAnswerRead]:
    """Gửi câu trả lời cho một câu hỏi và nhận điểm/feedback do AI chấm."""
    answer = await submit_interview_answer(
        db,
        user_id=current_user.id,
        session_id=session_id,
        question_id=payload.question_id,
        answer_text=payload.answer_text,
    )
    return ApiResponse(
        data=InterviewAnswerRead.model_validate(answer),
        message="Đã chấm điểm câu trả lời.",
    )


@router.post("/{session_id}/complete", response_model=InterviewSessionResponse)
def complete_interview(
    session_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> ApiResponse[InterviewSessionRead]:
    """Hoàn thành phiên và trả về điểm tổng hợp cùng toàn bộ câu trả lời."""
    session = complete_interview_session(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    return ApiResponse(
        data=InterviewSessionRead.model_validate(session),
        message="Hoàn thành phiên phỏng vấn thành công.",
    )
