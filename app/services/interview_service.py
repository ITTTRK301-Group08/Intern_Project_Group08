"""Nghiệp vụ phỏng vấn thử: tạo phiên, chấm câu trả lời và hoàn thành phiên."""

from __future__ import annotations

import asyncio
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.career import CareerRole
from app.models.interview import (
    InterviewAnswer,
    InterviewQuestion,
    InterviewSession,
)
from app.prompts.mock_interview import (
    INTERVIEW_SCORING_SYSTEM_INSTRUCTION,
    MOCK_INTERVIEW_SYSTEM_INSTRUCTION,
    InterviewAnswerContext,
    InterviewSkillContext,
    build_interview_answer_scoring_prompt,
    build_mock_interview_prompt,
)
from app.schemas.analysis import AIConsent
from app.schemas.interview.ai_response import (
    InterviewAnswerScoreAI,
    InterviewGenerationAIResponse,
)
from app.schemas.interview.request import ANSWER_MAX_LENGTH
from app.services.ai import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AIService,
    AIServiceError,
    AITimeoutError,
    get_ai_service,
)
from app.services.analysis_service import validate_ai_consent
from app.services.catalog_service import get_role_by_id

logger = logging.getLogger(__name__)

# Nghiệp vụ Mock Interview yêu cầu đúng 3 câu hỏi cho mỗi phiên.
REQUIRED_QUESTION_COUNT = 3

CAREER_ROLE_NOT_FOUND = "INTERVIEW_CAREER_ROLE_NOT_FOUND"
CAREER_ROLE_INACTIVE = "INTERVIEW_CAREER_ROLE_INACTIVE"
CAREER_ROLE_SKILLS_REQUIRED = "INTERVIEW_ROLE_SKILLS_REQUIRED"
SESSION_NOT_FOUND = "INTERVIEW_SESSION_NOT_FOUND"
SESSION_FORBIDDEN = "INTERVIEW_SESSION_FORBIDDEN"
QUESTION_NOT_FOUND = "INTERVIEW_QUESTION_NOT_FOUND"
ANSWER_REQUIRED = "INTERVIEW_ANSWER_REQUIRED"
ANSWER_TOO_LONG = "INTERVIEW_ANSWER_TOO_LONG"
ANSWER_ALREADY_SUBMITTED = "INTERVIEW_ANSWER_ALREADY_SUBMITTED"
SESSION_COMPLETED = "INTERVIEW_SESSION_COMPLETED"
SESSION_ABANDONED = "INTERVIEW_SESSION_ABANDONED"
SESSION_NOT_ACTIVE = "INTERVIEW_SESSION_NOT_ACTIVE"
ANSWERS_INCOMPLETE = "INTERVIEW_ANSWERS_INCOMPLETE"
AI_TIMEOUT = "INTERVIEW_AI_TIMEOUT"
AI_AUTHENTICATION_FAILED = "INTERVIEW_AI_AUTHENTICATION_FAILED"
AI_RATE_LIMITED = "INTERVIEW_AI_RATE_LIMITED"
AI_INVALID_REQUEST = "INTERVIEW_AI_INVALID_REQUEST"
AI_UNAVAILABLE = "INTERVIEW_AI_UNAVAILABLE"
AI_INVALID_RESPONSE = "INTERVIEW_AI_INVALID_RESPONSE"
AI_DUPLICATE_QUESTIONS = "INTERVIEW_AI_DUPLICATE_QUESTIONS"
DATABASE_ERROR = "INTERVIEW_DATABASE_ERROR"

DEFAULT_INVALID_RESPONSE_MESSAGE = (
    "Dịch vụ AI trả về dữ liệu câu hỏi không hợp lệ."
)
SCORING_INVALID_RESPONSE_MESSAGE = (
    "Dịch vụ AI trả về điểm hoặc nhận xét không hợp lệ."
)


def abandon_stale_interview_sessions(
    db: Session,
    *,
    user_id: int,
    now: datetime | None = None,
) -> int:
    """Mark open interview sessions idle for more than 24 hours as abandoned."""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is not None:
        current_time = current_time.astimezone(timezone.utc).replace(tzinfo=None)
    cutoff = current_time - INTERVIEW_IDLE_TIMEOUT

    try:
        result = db.execute(
            update(InterviewSession)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.status.in_(OPEN_INTERVIEW_STATUSES),
                InterviewSession.updated_at < cutoff,
            )
            .values(status="abandoned")
        )
        affected = result.rowcount or 0
        if affected:
            db.commit()
        return affected
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Không thể tự động đóng phiên phỏng vấn bị bỏ dở.")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể cập nhật trạng thái phiên phỏng vấn.",
        ) from exc


def _error(status_code: int, code: str, message: str) -> HTTPException:
    """Tạo HTTPException theo error format hiện tại của dự án."""
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "data": {"code": code}, "message": message},
    )


def _map_ai_error(
    exc: AIServiceError,
    *,
    invalid_response_message: str = DEFAULT_INVALID_RESPONSE_MESSAGE,
) -> HTTPException:
    """Chuyển exception AI thành lỗi HTTP an toàn cho Client.

    Không đưa thông điệp gốc của SDK, API Key hay traceback vào response.
    """
    if isinstance(exc, AITimeoutError):
        return _error(
            status.HTTP_504_GATEWAY_TIMEOUT,
            AI_TIMEOUT,
            "Dịch vụ AI phản hồi quá thời gian chờ. Vui lòng thử lại sau.",
        )
    if isinstance(exc, AIRateLimitError):
        return _error(
            status.HTTP_429_TOO_MANY_REQUESTS,
            AI_RATE_LIMITED,
            "Dịch vụ AI đang giới hạn số lượng yêu cầu. Vui lòng thử lại sau.",
        )
    if isinstance(exc, AIAuthenticationError):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            AI_AUTHENTICATION_FAILED,
            "Không thể xác thực với dịch vụ AI. Vui lòng liên hệ quản trị viên.",
        )
    if isinstance(exc, AIInvalidRequestError):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            AI_INVALID_REQUEST,
            "Yêu cầu gửi tới dịch vụ AI không hợp lệ.",
        )
    if isinstance(exc, AIConfigurationError):
        return _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            AI_UNAVAILABLE,
            "Dịch vụ AI chưa được cấu hình hoặc đang không khả dụng.",
        )
    if isinstance(exc, AIResponseValidationError):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            AI_INVALID_RESPONSE,
            invalid_response_message,
        )
    if isinstance(exc, AIProviderError):
        return _error(
            status.HTTP_502_BAD_GATEWAY,
            AI_UNAVAILABLE,
            "Dịch vụ AI đang gặp lỗi. Vui lòng thử lại sau.",
        )
    return _error(
        status.HTTP_502_BAD_GATEWAY,
        AI_UNAVAILABLE,
        "Dịch vụ AI đang gặp lỗi không xác định. Vui lòng thử lại sau.",
    )


def _utcnow() -> datetime:
    """Thời điểm UTC dạng naive để tương thích cột DateTime hiện có."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _load_role_with_skills(db: Session, career_role_id: int) -> CareerRole:
    """Lấy vị trí nghề nghiệp đang hoạt động cùng kỹ năng liên quan."""
    try:
        role = get_role_by_id(db, career_role_id, include_inactive=True)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise _error(
                status.HTTP_404_NOT_FOUND,
                CAREER_ROLE_NOT_FOUND,
                "Không tìm thấy vị trí nghề nghiệp.",
            ) from exc
        raise

    if not role.is_active:
        raise _error(
            status.HTTP_409_CONFLICT,
            CAREER_ROLE_INACTIVE,
            "Vị trí nghề nghiệp đã ngừng hoạt động.",
        )
    if not role.required_skills:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            CAREER_ROLE_SKILLS_REQUIRED,
            "Vị trí nghề nghiệp chưa có kỹ năng liên quan để sinh câu hỏi.",
        )
    return role


def _build_skill_contexts(role: CareerRole) -> list[InterviewSkillContext]:
    """Chuyển kỹ năng của vị trí thành dữ liệu tối thiểu cho prompt.

    Sắp xếp theo trọng số và mức yêu cầu giảm dần để AI ưu tiên đúng
    những kỹ năng quan trọng nhất của vị trí.
    """
    ordered = sorted(
        role.required_skills,
        key=lambda item: (
            -float(item.weight),
            -item.required_level,
            item.skill_id,
        ),
    )
    return [
        InterviewSkillContext(
            name=item.skill.name,
            required_level=item.required_level,
            is_required=bool(item.is_required),
        )
        for item in ordered
        if item.skill is not None
    ]


def _normalize_question_text(text: str) -> str:
    """Chuẩn hóa nội dung câu hỏi để phát hiện trùng lặp rõ ràng."""
    return " ".join(text.casefold().split())


def _validate_generated_questions(result: InterviewGenerationAIResponse) -> None:
    """Kiểm tra lại số lượng và tính duy nhất của câu hỏi do AI sinh.

    Pydantic đã giới hạn đúng 3 câu hỏi, nhưng vẫn kiểm tra lại ở tầng
    nghiệp vụ để không phụ thuộc duy nhất vào schema hoặc prompt.
    """
    if len(result.questions) != REQUIRED_QUESTION_COUNT:
        raise _error(
            status.HTTP_502_BAD_GATEWAY,
            AI_INVALID_RESPONSE,
            "Dịch vụ AI không sinh đúng 3 câu hỏi.",
        )

    normalized = [
        _normalize_question_text(question.question_text)
        for question in result.questions
    ]
    if len(set(normalized)) != len(normalized):
        raise _error(
            status.HTTP_502_BAD_GATEWAY,
            AI_DUPLICATE_QUESTIONS,
            "Dịch vụ AI sinh câu hỏi trùng lặp nội dung.",
        )


def _abandon_previous_sessions(
    db: Session,
    *,
    user_id: int,
    career_role_id: int,
) -> None:
    """D1: chỉ đóng các phiên in_progress cũ cùng vị trí khi tạo phiên mới."""
    db.execute(
        update(InterviewSession)
        .where(
            InterviewSession.user_id == user_id,
            InterviewSession.career_role_id == career_role_id,
            InterviewSession.status == "in_progress",
        )
        .values(status="abandoned", updated_at=func.current_timestamp())
    )


def _persist_session(
    db: Session,
    *,
    user_id: int,
    career_role_id: int,
    questions: list[tuple[str, str, list[str]]],
) -> InterviewSession:
    """Lưu phiên phỏng vấn và các câu hỏi trong cùng một transaction."""
    session = InterviewSession(
        user_id=user_id,
        career_role_id=career_role_id,
        status="ready",
    )

    try:
        db.add(session)
        db.flush()

        for order, (question_text, competency, criteria) in enumerate(
            questions, start=1
        ):
            db.add(
                InterviewQuestion(
                    session_id=session.id,
                    question_text=question_text,
                    competency=competency,
                    evaluation_criteria=list(criteria),
                    question_order=order,
                )
            )

        db.commit()

        created_session = db.scalar(
            select(InterviewSession)
            .options(
                joinedload(InterviewSession.career_role),
                selectinload(InterviewSession.questions),
            )
            .where(InterviewSession.id == session.id)
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Không lưu được phiên phỏng vấn vào database.")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể lưu phiên phỏng vấn. Vui lòng thử lại.",
        ) from exc

    if created_session is None:
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể đọc lại phiên phỏng vấn vừa tạo.",
        )
    return created_session


async def create_interview_session(
    db: Session,
    *,
    user_id: int,
    career_role_id: int,
    consent: AIConsent,
    ai_service: AIService | None = None,
) -> InterviewSession:
    """Tạo phiên phỏng vấn và lưu bộ 3 câu hỏi đã được xác thực.

    Chỉ ghi database sau khi AI trả về đúng 3 câu hỏi hợp lệ. Nếu bất kỳ
    bước nào thất bại, không có session hoặc câu hỏi nào được lưu.
    """
    # 1) Consent phải được kiểm tra trước khi truy vấn hoặc gọi AI.
    validate_ai_consent(consent)

    # 2) Xác thực vị trí nghề nghiệp và lấy kỹ năng liên quan từ catalog.
    role = _load_role_with_skills(db, career_role_id)
    role_id = role.id
    skills = _build_skill_contexts(role)
    if not skills:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            CAREER_ROLE_SKILLS_REQUIRED,
            "Vị trí nghề nghiệp chưa có kỹ năng liên quan để sinh câu hỏi.",
        )

    # 3) Dựng prompt chỉ từ dữ liệu catalog công khai.
    prompt = build_mock_interview_prompt(
        career_role_name=role.name,
        career_role_level=role.level,
        career_role_description=role.description,
        skills=skills,
    )

    # 4) Gọi AI Service của Task 1; không gọi SDK Gemini trực tiếp.
    try:
        service = ai_service or get_ai_service()
        ai_result = await service.generate_structured(
            prompt=prompt,
            response_schema=InterviewGenerationAIResponse,
            system_instruction=MOCK_INTERVIEW_SYSTEM_INSTRUCTION,
        )
    except AIServiceError as exc:
        db.rollback()
        logger.warning(
            "Sinh câu hỏi phỏng vấn thất bại với mã lỗi AI %s.",
            exc.code,
        )
        raise _map_ai_error(exc) from exc

    # 5) Kiểm tra lại số lượng và nội dung trùng lặp ở tầng nghiệp vụ.
    try:
        _validate_generated_questions(ai_result)
    except HTTPException:
        db.rollback()
        raise

    # 6) Lưu session và 3 câu hỏi trong cùng một transaction.
    questions = [
        (
            question.question_text,
            question.competency,
            question.evaluation_criteria,
        )
        for question in ai_result.questions
    ]
    return _persist_session(
        db,
        user_id=user_id,
        career_role_id=role_id,
        questions=questions,
    )


# ---------------------------------------------------------------------------
# Truy vấn phiên và kiểm tra quyền sở hữu
# ---------------------------------------------------------------------------


def _get_owned_session(
    db: Session,
    *,
    session_id: int,
    user_id: int,
    with_questions: bool = False,
) -> InterviewSession:
    """Lấy phiên và bảo đảm phiên thuộc đúng người dùng hiện tại."""
    statement = (
        select(InterviewSession)
        .options(joinedload(InterviewSession.career_role))
        .where(InterviewSession.id == session_id)
    )
    if with_questions:
        statement = statement.options(
            selectinload(InterviewSession.questions).selectinload(
                InterviewQuestion.answer
            )
        )

    session = db.scalars(statement).unique().one_or_none()
    if session is None:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            SESSION_NOT_FOUND,
            "Không tìm thấy phiên phỏng vấn.",
        )
    if session.user_id != user_id:
        raise _error(
            status.HTTP_403_FORBIDDEN,
            SESSION_FORBIDDEN,
            "Bạn không có quyền truy cập phiên phỏng vấn này.",
        )
    return session


def _get_question_in_session(
    db: Session,
    *,
    session_id: int,
    question_id: int,
) -> InterviewQuestion:
    """Lấy câu hỏi và bảo đảm câu hỏi thuộc phiên đang xử lý."""
    question = db.scalar(
        select(InterviewQuestion).where(InterviewQuestion.id == question_id)
    )
    if question is None or question.session_id != session_id:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            QUESTION_NOT_FOUND,
            "Không tìm thấy câu hỏi trong phiên phỏng vấn này.",
        )
    return question


def _ensure_session_active(session: InterviewSession) -> None:
    """Chỉ cho thao tác trên phiên ready/in_progress."""
    if session.status == "completed":
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_COMPLETED,
            "Phiên phỏng vấn đã hoàn thành, không thể thay đổi.",
        )
    if session.status == "abandoned":
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_ABANDONED,
            "Phiên phỏng vấn đã bị bỏ dở, không thể thay đổi.",
        )
    if session.status not in ACTIVE_SESSION_STATUSES:
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_NOT_ACTIVE,
            "Phiên phỏng vấn không ở trạng thái có thể thao tác.",
        )


def _answer_exists(db: Session, *, question_id: int) -> bool:
    """Kiểm tra câu hỏi đã có câu trả lời hay chưa."""
    return (
        db.scalar(
            select(InterviewAnswer.id).where(
                InterviewAnswer.question_id == question_id
            )
        )
        is not None
    )


def get_interview_questions(
    db: Session,
    *,
    user_id: int,
    session_id: int,
) -> list[InterviewQuestion]:
    """Trả về câu hỏi của phiên theo đúng thứ tự."""
    session = _get_owned_session(
        db,
        session_id=session_id,
        user_id=user_id,
        with_questions=True,
    )
    return sorted(session.questions, key=lambda item: item.question_order)


def get_interview_session_detail(
    db: Session,
    *,
    user_id: int,
    session_id: int,
) -> InterviewSession:
    """Trả về chi tiết phiên kèm câu hỏi, điểm và feedback."""
    session = _get_owned_session(
        db,
        session_id=session_id,
        user_id=user_id,
        with_questions=True,
    )
    session.questions.sort(key=lambda item: item.question_order)
    return session


def list_interview_sessions(
    db: Session,
    *,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """Liệt kê phiên của chính người dùng hiện tại, mới nhất trước."""
    offset = max(0, (page - 1) * page_size)
    total = (
        db.scalar(
            select(func.count(InterviewSession.id)).where(
                InterviewSession.user_id == user_id
            )
        )
        or 0
    )
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1

    sessions = (
        db.scalars(
            select(InterviewSession)
            .options(
                joinedload(InterviewSession.career_role),
                selectinload(InterviewSession.questions).selectinload(
                    InterviewQuestion.answer
                ),
            )
            .where(InterviewSession.user_id == user_id)
            .order_by(desc(InterviewSession.created_at), desc(InterviewSession.id))
            .offset(offset)
            .limit(page_size)
        )
        .unique()
        .all()
    )

    items = []
    for session in sessions:
        questions = session.questions or []
        answered = sum(1 for question in questions if question.answer is not None)
        items.append(
            {
                "id": session.id,
                "career_role_id": session.career_role_id,
                "career_role_name": (
                    session.career_role.name if session.career_role else None
                ),
                "status": session.status,
                "question_count": len(questions),
                "answered_count": answered,
                "total_score": session.total_score,
                "created_at": session.created_at,
                "completed_at": session.completed_at,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------------------------
# Chấm điểm câu trả lời
# ---------------------------------------------------------------------------


def _validate_answer_text(answer_text: str) -> str:
    """Kiểm tra lại câu trả lời ở tầng service (phòng khi gọi trực tiếp)."""
    normalized = (answer_text or "").strip()
    if not normalized:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ANSWER_REQUIRED,
            "Câu trả lời không được để trống.",
        )
    if len(normalized) > ANSWER_MAX_LENGTH:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ANSWER_TOO_LONG,
            f"Câu trả lời không được vượt quá {ANSWER_MAX_LENGTH} ký tự.",
        )
    return normalized


def _validate_ai_score(result: InterviewAnswerScoreAI) -> tuple[Decimal, str]:
    """Xác thực lại score/feedback trước khi lưu; không clamp dữ liệu sai."""
    score = result.score
    if not score.is_finite() or score < 0 or score > 100:
        raise _error(
            status.HTTP_502_BAD_GATEWAY,
            AI_INVALID_RESPONSE,
            SCORING_INVALID_RESPONSE_MESSAGE,
        )

    feedback = (result.feedback or "").strip()
    if not feedback:
        raise _error(
            status.HTTP_502_BAD_GATEWAY,
            AI_INVALID_RESPONSE,
            SCORING_INVALID_RESPONSE_MESSAGE,
        )

    return score.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP), feedback


async def _score_answer(
    *,
    session: InterviewSession,
    question: InterviewQuestion,
    answer_text: str,
    ai_service: AIService | None,
) -> tuple[Decimal, str]:
    """Gọi AI chấm điểm trước khi mở transaction ghi database."""
    role = session.career_role
    prompt = build_interview_answer_scoring_prompt(
        career_role_name=role.name if role else "Vị trí ứng tuyển",
        career_role_level=role.level if role else "Không xác định",
        question=InterviewAnswerContext(
            question_text=question.question_text,
            competency=question.competency,
            evaluation_criteria=list(question.evaluation_criteria or []),
        ),
        answer_text=answer_text,
    )

    try:
        service = ai_service or get_ai_service()
        # D2: giới hạn tổng thời gian chờ AI, kể cả khi provider retry.
        result = await asyncio.wait_for(
            service.generate_structured(
                prompt=prompt,
                response_schema=InterviewAnswerScoreAI,
                system_instruction=INTERVIEW_SCORING_SYSTEM_INSTRUCTION,
            ),
            timeout=SCORING_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise _error(
            status.HTTP_504_GATEWAY_TIMEOUT,
            AI_TIMEOUT,
            "Dịch vụ AI phản hồi quá thời gian chờ. Vui lòng thử lại sau.",
        ) from exc
    except AIServiceError as exc:
        logger.warning(
            "Chấm điểm câu trả lời thất bại với mã lỗi AI %s.",
            exc.code,
        )
        raise _map_ai_error(
            exc,
            invalid_response_message=SCORING_INVALID_RESPONSE_MESSAGE,
        ) from exc

    return _validate_ai_score(result)


def _persist_answer(
    db: Session,
    *,
    session_id: int,
    question_id: int,
    user_id: int,
    answer_text: str,
    score: Decimal,
    feedback: str,
) -> dict:
    """Ghi answer sau khi đã có điểm AI, kiểm tra lại trạng thái trong transaction."""
    try:
        # Re-check sau khi AI trả lời: trạng thái có thể đã thay đổi trong lúc chờ.
        session = db.scalars(
            select(InterviewSession).where(InterviewSession.id == session_id)
        ).one_or_none()
        if session is None:
            raise _error(
                status.HTTP_404_NOT_FOUND,
                SESSION_NOT_FOUND,
                "Không tìm thấy phiên phỏng vấn.",
            )
        if session.user_id != user_id:
            raise _error(
                status.HTTP_403_FORBIDDEN,
                SESSION_FORBIDDEN,
                "Bạn không có quyền truy cập phiên phỏng vấn này.",
            )
        _ensure_session_active(session)

        question = db.scalar(
            select(InterviewQuestion).where(
                InterviewQuestion.id == question_id,
                InterviewQuestion.session_id == session_id,
            )
        )
        if question is None:
            raise _error(
                status.HTTP_404_NOT_FOUND,
                QUESTION_NOT_FOUND,
                "Không tìm thấy câu hỏi trong phiên phỏng vấn này.",
            )

        if _answer_exists(db, question_id=question_id):
            raise _error(
                status.HTTP_409_CONFLICT,
                ANSWER_ALREADY_SUBMITTED,
                "Câu hỏi này đã được trả lời.",
            )

        answer = InterviewAnswer(
            question_id=question_id,
            answer_text=answer_text,
            score=score,
            feedback=feedback,
        )
        db.add(answer)
        if session.status == "ready":
            session.status = "in_progress"
        session.updated_at = _utcnow()
        db.commit()
        db.refresh(answer)

        question_count = (
            db.scalar(
                select(func.count(InterviewQuestion.id)).where(
                    InterviewQuestion.session_id == session_id
                )
            )
            or 0
        )
        answered_count = (
            db.scalar(
                select(func.count(InterviewAnswer.id))
                .join(
                    InterviewQuestion,
                    InterviewAnswer.question_id == InterviewQuestion.id,
                )
                .where(InterviewQuestion.session_id == session_id)
            )
            or 0
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        # Hai request đồng thời có thể vượt qua kiểm tra trước khi unique
        # constraint của question_id chặn lại.
        db.rollback()
        raise _error(
            status.HTTP_409_CONFLICT,
            ANSWER_ALREADY_SUBMITTED,
            "Câu hỏi này đã được trả lời.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Không lưu được câu trả lời phỏng vấn vào database.")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể lưu câu trả lời. Vui lòng thử lại.",
        ) from exc

    return {
        "answer": answer,
        "session_status": session.status,
        "question_count": question_count,
        "answered_count": answered_count,
    }


async def submit_interview_answer(
    db: Session,
    *,
    user_id: int,
    session_id: int,
    question_id: int,
    answer_text: str,
    ai_service: AIService | None = None,
) -> dict:
    """Chấm và lưu câu trả lời cho một câu hỏi thuộc phiên hiện tại.

    AI được gọi ngoài transaction ghi database để không giữ lock trong lúc
    chờ. Nếu AI lỗi hoặc dữ liệu AI không hợp lệ, answer không được lưu.
    """
    normalized_answer = _validate_answer_text(answer_text)

    session = _get_owned_session(
        db,
        session_id=session_id,
        user_id=user_id,
    )
    _ensure_session_active(session)
    question = _get_question_in_session(
        db,
        session_id=session_id,
        question_id=question_id,
    )
    if _answer_exists(db, question_id=question_id):
        raise _error(
            status.HTTP_409_CONFLICT,
            ANSWER_ALREADY_SUBMITTED,
            "Câu hỏi này đã được trả lời.",
        )

    score, feedback = await _score_answer(
        session=session,
        question=question,
        answer_text=normalized_answer,
        ai_service=ai_service,
    )

    return _persist_answer(
        db,
        session_id=session_id,
        question_id=question_id,
        user_id=user_id,
        answer_text=normalized_answer,
        score=score,
        feedback=feedback,
    )


# ---------------------------------------------------------------------------
# Hoàn thành phiên
# ---------------------------------------------------------------------------


def complete_interview_session(
    db: Session,
    *,
    user_id: int,
    session_id: int,
) -> dict:
    """Hoàn thành phiên khi đủ câu trả lời và tính điểm trung bình."""
    try:
        session = _get_owned_session(
            db,
            session_id=session_id,
            user_id=user_id,
            with_questions=True,
        )
        if session.status == "completed":
            raise _error(
                status.HTTP_409_CONFLICT,
                SESSION_COMPLETED,
                "Phiên phỏng vấn đã hoàn thành.",
            )
        if session.status == "abandoned":
            raise _error(
                status.HTTP_409_CONFLICT,
                SESSION_ABANDONED,
                "Phiên phỏng vấn đã bị bỏ dở, không thể hoàn thành.",
            )
        if session.status not in ACTIVE_SESSION_STATUSES:
            raise _error(
                status.HTTP_409_CONFLICT,
                SESSION_NOT_ACTIVE,
                "Phiên phỏng vấn không ở trạng thái có thể hoàn thành.",
            )

        questions = sorted(
            session.questions or [],
            key=lambda item: item.question_order,
        )
        missing = [question for question in questions if question.answer is None]
        if not questions or missing:
            raise _error(
                status.HTTP_409_CONFLICT,
                ANSWERS_INCOMPLETE,
                "Vui lòng trả lời đầy đủ tất cả câu hỏi trước khi hoàn thành phiên.",
            )

        scores = [Decimal(question.answer.score) for question in questions]
        total_score = (
            sum(scores, Decimal("0")) / Decimal(len(scores))
        ).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)

        completed_at = _utcnow()
        session.status = "completed"
        session.total_score = total_score
        session.completed_at = completed_at
        session.updated_at = completed_at
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Không hoàn thành được phiên phỏng vấn.")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể hoàn thành phiên phỏng vấn. Vui lòng thử lại.",
        ) from exc

    return {
        "id": session.id,
        "status": session.status,
        "total_score": total_score,
        "completed_at": completed_at,
        "question_count": len(questions),
        "answered_count": len(scores),
    }
