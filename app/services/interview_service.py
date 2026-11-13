"""Nghiệp vụ phỏng vấn thử (M6).

Bao gồm tạo phiên với đúng 3 câu hỏi, gửi câu trả lời và chấm điểm từng câu,
hoàn thành phiên với điểm trung bình cộng, cùng lịch sử/chi tiết phiên.
Các thao tác ghi đều dùng transaction và kiểm tra quyền sở hữu từ JWT.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.career import CareerRole
from app.models.interview import InterviewAnswer, InterviewQuestion, InterviewSession
from app.prompts.mock_interview import (
    INTERVIEW_GRADING_SYSTEM_INSTRUCTION,
    MOCK_INTERVIEW_SYSTEM_INSTRUCTION,
    InterviewSkillContext,
    build_interview_grading_prompt,
    build_mock_interview_prompt,
)
from app.schemas.analysis import AIConsent
from app.schemas.interview.ai_response import (
    InterviewAnswerGradeAI,
    InterviewGenerationAIResponse,
)
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
# Phiên không tương tác quá 24 giờ được coi là bỏ dở (FR-INT-08).
ABANDON_AFTER = timedelta(hours=24)

CAREER_ROLE_NOT_FOUND = "INTERVIEW_CAREER_ROLE_NOT_FOUND"
CAREER_ROLE_INACTIVE = "INTERVIEW_CAREER_ROLE_INACTIVE"
CAREER_ROLE_SKILLS_REQUIRED = "INTERVIEW_ROLE_SKILLS_REQUIRED"
AI_TIMEOUT = "INTERVIEW_AI_TIMEOUT"
AI_AUTHENTICATION_FAILED = "INTERVIEW_AI_AUTHENTICATION_FAILED"
AI_RATE_LIMITED = "INTERVIEW_AI_RATE_LIMITED"
AI_INVALID_REQUEST = "INTERVIEW_AI_INVALID_REQUEST"
AI_UNAVAILABLE = "INTERVIEW_AI_UNAVAILABLE"
AI_INVALID_RESPONSE = "INTERVIEW_AI_INVALID_RESPONSE"
AI_DUPLICATE_QUESTIONS = "INTERVIEW_AI_DUPLICATE_QUESTIONS"
DATABASE_ERROR = "INTERVIEW_DATABASE_ERROR"
SESSION_NOT_FOUND = "INTERVIEW_NOT_FOUND"
QUESTION_NOT_FOUND = "INTERVIEW_QUESTION_NOT_FOUND"
ANSWER_ALREADY_EXISTS = "INTERVIEW_ANSWER_ALREADY_EXISTS"
SESSION_NOT_IN_PROGRESS = "INTERVIEW_NOT_IN_PROGRESS"
SESSION_ABANDONED = "INTERVIEW_ABANDONED"
SESSION_INCOMPLETE = "INTERVIEW_INCOMPLETE"


def _error(status_code: int, code: str, message: str) -> HTTPException:
    """Tạo HTTPException theo error format hiện tại của dự án."""
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "data": {"code": code}, "message": message},
    )


def _utcnow() -> datetime:
    """Trả thời gian UTC dạng naive để đồng bộ với cột DATETIME."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _round_score(value: float) -> Decimal:
    """Làm tròn điểm về tối đa 2 chữ số thập phân."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _map_ai_error(exc: AIServiceError) -> HTTPException:
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
            "Dịch vụ AI trả về dữ liệu không hợp lệ.",
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


def _abandon_sessions(
    db: Session,
    *,
    user_id: int,
    now: datetime,
    career_role_id: int | None = None,
    commit: bool,
) -> None:
    """Chuyển các phiên ``in_progress`` cần bỏ dở sang ``abandoned``.

    Một phiên bị bỏ dở khi quá 24 giờ không tương tác, hoặc khi sinh viên
    tạo phiên mới cùng vị trí (FR-INT-08).
    """
    conditions = [
        InterviewSession.user_id == user_id,
        InterviewSession.status == "in_progress",
    ]
    stale_or_same_role = InterviewSession.updated_at < now - ABANDON_AFTER
    if career_role_id is not None:
        stale_or_same_role = or_(
            stale_or_same_role,
            InterviewSession.career_role_id == career_role_id,
        )
    conditions.append(stale_or_same_role)

    db.execute(
        update(InterviewSession)
        .where(*conditions)
        .values(status="abandoned", updated_at=now)
    )
    if commit:
        db.commit()


def _persist_session(
    db: Session,
    *,
    user_id: int,
    career_role_id: int,
    questions: list[tuple[str, str, list[str]]],
    now: datetime,
) -> InterviewSession:
    """Lưu phiên phỏng vấn và các câu hỏi trong cùng một transaction."""
    session = InterviewSession(
        user_id=user_id,
        career_role_id=career_role_id,
        status="in_progress",
    )

    try:
        # Bỏ dở phiên cũ cùng vị trí trong cùng transaction với phiên mới.
        _abandon_sessions(
            db,
            user_id=user_id,
            now=now,
            career_role_id=career_role_id,
            commit=False,
        )
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

        created_session = _load_session_query(db, session.id, user_id)
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


def _load_session_query(
    db: Session,
    session_id: int,
    user_id: int,
) -> InterviewSession | None:
    """Truy vấn phiên kèm câu hỏi, câu trả lời và vị trí nghề nghiệp."""
    return db.scalar(
        select(InterviewSession)
        .options(
            joinedload(InterviewSession.career_role),
            selectinload(InterviewSession.questions).selectinload(
                InterviewQuestion.answer
            ),
        )
        .where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )


def get_session_for_user(
    db: Session,
    *,
    session_id: int,
    user_id: int,
) -> InterviewSession:
    """Lấy phiên thuộc đúng người dùng hiện tại."""
    session = _load_session_query(db, session_id, user_id)
    if session is None:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            SESSION_NOT_FOUND,
            "Không tìm thấy phiên phỏng vấn.",
        )
    return session


def list_sessions_for_user(
    db: Session,
    *,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[InterviewSession], int]:
    """Lấy lịch sử phiên phỏng vấn của người dùng hiện tại."""
    now = _utcnow()
    try:
        _abandon_sessions(db, user_id=user_id, now=now, commit=True)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Không cập nhật được trạng thái phiên bỏ dở.")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể tải lịch sử phỏng vấn. Vui lòng thử lại.",
        ) from exc

    total = db.scalar(
        select(func.count(InterviewSession.id)).where(
            InterviewSession.user_id == user_id
        )
    ) or 0
    sessions = list(
        db.scalars(
            select(InterviewSession)
            .options(joinedload(InterviewSession.career_role))
            .where(InterviewSession.user_id == user_id)
            .order_by(InterviewSession.created_at.desc(), InterviewSession.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return sessions, int(total)


def get_session_questions(
    db: Session,
    *,
    session_id: int,
    user_id: int,
) -> InterviewSession:
    """Lấy danh sách câu hỏi theo thứ tự của một phiên thuộc người dùng."""
    return get_session_for_user(db, session_id=session_id, user_id=user_id)


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

    # 4) Gọi AI Service dùng chung; không gọi SDK Gemini trực tiếp.
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
        now=_utcnow(),
    )


def _load_answerable_session(
    db: Session,
    *,
    session_id: int,
    user_id: int,
) -> InterviewSession:
    """Lấy phiên và kiểm tra phiên còn cho phép gửi câu trả lời."""
    session = get_session_for_user(db, session_id=session_id, user_id=user_id)
    if session.status == "abandoned":
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_ABANDONED,
            "Phiên phỏng vấn đã bị bỏ dở và không thể tiếp tục.",
        )
    if session.status == "completed":
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_NOT_IN_PROGRESS,
            "Phiên phỏng vấn đã hoàn thành.",
        )
    if session.status != "in_progress":
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_NOT_IN_PROGRESS,
            "Phiên phỏng vấn không ở trạng thái có thể trả lời.",
        )
    return session


async def submit_interview_answer(
    db: Session,
    *,
    user_id: int,
    session_id: int,
    question_id: int,
    answer_text: str,
    ai_service: AIService | None = None,
) -> InterviewAnswer:
    """Chấm điểm và lưu câu trả lời cho đúng một câu hỏi của phiên."""
    session = _load_answerable_session(db, session_id=session_id, user_id=user_id)

    question = next(
        (item for item in session.questions if item.id == question_id),
        None,
    )
    if question is None:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            QUESTION_NOT_FOUND,
            "Không tìm thấy câu hỏi trong phiên phỏng vấn.",
        )
    if question.answer is not None:
        raise _error(
            status.HTTP_409_CONFLICT,
            ANSWER_ALREADY_EXISTS,
            "Câu hỏi này đã được trả lời.",
        )

    normalized_answer = answer_text.strip()
    if not normalized_answer:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            QUESTION_NOT_FOUND,
            "Câu trả lời không được để trống.",
        )

    prompt = build_interview_grading_prompt(
        question_text=question.question_text,
        competency=question.competency,
        evaluation_criteria=question.evaluation_criteria,
        answer_text=normalized_answer,
    )

    try:
        service = ai_service or get_ai_service()
        grading = await service.generate_structured(
            prompt=prompt,
            response_schema=InterviewAnswerGradeAI,
            system_instruction=INTERVIEW_GRADING_SYSTEM_INSTRUCTION,
        )
    except AIServiceError as exc:
        db.rollback()
        logger.warning("Chấm điểm câu trả lời thất bại với mã lỗi AI %s.", exc.code)
        raise _map_ai_error(exc) from exc

    answer = InterviewAnswer(
        question_id=question.id,
        answer_text=normalized_answer,
        score=_round_score(grading.score),
        feedback=grading.feedback,
    )

    try:
        db.add(answer)
        # Ghi nhận tương tác để mốc 24 giờ tính từ lần trả lời gần nhất.
        session.updated_at = _utcnow()
        db.commit()
        db.refresh(answer)
    except IntegrityError as exc:
        db.rollback()
        raise _error(
            status.HTTP_409_CONFLICT,
            ANSWER_ALREADY_EXISTS,
            "Câu hỏi này đã được trả lời.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Không lưu được câu trả lời phỏng vấn.")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể lưu câu trả lời. Vui lòng thử lại.",
        ) from exc

    return answer


def complete_interview_session(
    db: Session,
    *,
    user_id: int,
    session_id: int,
) -> InterviewSession:
    """Hoàn thành phiên và tính điểm tổng bằng trung bình cộng các câu.

    Không gọi lại AI. Chỉ chuyển ``completed`` khi mọi câu hỏi đã có câu trả lời
    và điểm được lưu đầy đủ.
    """
    session = get_session_for_user(db, session_id=session_id, user_id=user_id)

    if session.status == "completed":
        return session
    if session.status == "abandoned":
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_ABANDONED,
            "Phiên phỏng vấn đã bị bỏ dở và không thể hoàn thành.",
        )

    questions = list(session.questions)
    if len(questions) != REQUIRED_QUESTION_COUNT:
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_INCOMPLETE,
            "Phiên phỏng vấn không có đủ số câu hỏi bắt buộc.",
        )
    if any(question.answer is None for question in questions):
        raise _error(
            status.HTTP_409_CONFLICT,
            SESSION_INCOMPLETE,
            "Vui lòng trả lời đầy đủ tất cả câu hỏi trước khi hoàn thành.",
        )

    scores = [float(question.answer.score) for question in questions]
    total = sum(scores) / len(scores)
    now = _utcnow()

    try:
        session.total_score = _round_score(total)
        session.status = "completed"
        session.completed_at = now
        session.updated_at = now
        db.commit()
        refreshed = _load_session_query(db, session.id, user_id)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Không hoàn thành được phiên phỏng vấn.")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể hoàn thành phiên phỏng vấn. Vui lòng thử lại.",
        ) from exc

    if refreshed is None:
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể đọc lại phiên phỏng vấn vừa hoàn thành.",
        )
    return refreshed
