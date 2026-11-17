"""Nghiệp vụ tạo phiên phỏng vấn thử và sinh đúng 3 câu hỏi bằng AI."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.career import CareerRole
from app.models.interview import InterviewQuestion, InterviewSession
from app.prompts.mock_interview import (
    MOCK_INTERVIEW_SYSTEM_INSTRUCTION,
    InterviewSkillContext,
    build_mock_interview_prompt,
)
from app.schemas.analysis import AIConsent
from app.schemas.interview.ai_response import InterviewGenerationAIResponse
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
AI_TIMEOUT = "INTERVIEW_AI_TIMEOUT"
AI_AUTHENTICATION_FAILED = "INTERVIEW_AI_AUTHENTICATION_FAILED"
AI_RATE_LIMITED = "INTERVIEW_AI_RATE_LIMITED"
AI_INVALID_REQUEST = "INTERVIEW_AI_INVALID_REQUEST"
AI_UNAVAILABLE = "INTERVIEW_AI_UNAVAILABLE"
AI_INVALID_RESPONSE = "INTERVIEW_AI_INVALID_RESPONSE"
AI_DUPLICATE_QUESTIONS = "INTERVIEW_AI_DUPLICATE_QUESTIONS"
DATABASE_ERROR = "INTERVIEW_DATABASE_ERROR"


def _error(status_code: int, code: str, message: str) -> HTTPException:
    """Tạo HTTPException theo error format hiện tại của dự án."""
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "data": {"code": code}, "message": message},
    )


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
            "Dịch vụ AI trả về dữ liệu câu hỏi không hợp lệ.",
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
