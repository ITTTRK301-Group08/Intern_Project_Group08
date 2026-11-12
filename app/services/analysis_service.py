"""Nghiệp vụ phân tích khoảng cách kỹ năng (M4).

Luồng xử lý:
1. Kiểm tra consent, quyền sở hữu CV và vị trí mục tiêu (đồng bộ).
2. Tạo báo cáo ``processing`` và trả 202 ngay cho Client.
3. Tác vụ nền đọc lại dữ liệu, gọi AI, để backend tự tính ``gap_score`` và
   ``readiness_score``, rồi lưu toàn bộ kết quả trong một transaction.
4. Chỉ chuyển ``completed`` khi mọi kỹ năng đã được ghi; lỗi giữa chừng thì
   rollback và chuyển ``failed`` mà không lưu kết quả từng phần.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database.connection import SessionLocal
from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import CareerRole
from app.models.cv import CV
from app.models.profile_data import CareerRoleSkill, ProfileSkill
from app.models.student_profile import StudentProfile
from app.prompts.skill_gap_analysis import (
    SKILL_GAP_SYSTEM_INSTRUCTION,
    SkillAnalysisContext,
    build_profile_summary,
    build_skill_gap_prompt,
)
from app.schemas.analysis import SUPPORTED_PURPOSE_VERSION, AIConsent
from app.schemas.analysis_ai import SkillGapAnalysisAI
from app.services.ai import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AIServiceError,
    AITimeoutError,
    get_ai_service,
)
from app.services.catalog_service import get_role_by_id

logger = logging.getLogger(__name__)

# Factory có thể monkeypatch trong test để tác vụ nền dùng đúng database test.
_session_factory = SessionLocal

CONSENT_REQUIRED = "AI_CONSENT_REQUIRED"
CONSENT_VERSION_UNSUPPORTED = "AI_CONSENT_VERSION_UNSUPPORTED"
CV_NOT_FOUND = "CV_NOT_FOUND"
CV_FORBIDDEN = "CV_FORBIDDEN"
CAREER_ROLE_NOT_FOUND = "ANALYSIS_CAREER_ROLE_NOT_FOUND"
CAREER_ROLE_INACTIVE = "ANALYSIS_CAREER_ROLE_INACTIVE"
ROLE_SKILLS_REQUIRED = "ANALYSIS_ROLE_SKILLS_REQUIRED"
ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"
DATABASE_ERROR = "ANALYSIS_DATABASE_ERROR"
INVALID_AI_RESULT = "ANALYSIS_INVALID_AI_RESULT"

MARKET_SOURCE = "Danh mục nghề nghiệp nội bộ"


class AnalysisPipelineError(Exception):
    """Lỗi nghiệp vụ trong pipeline nền, chỉ dùng mã lỗi an toàn."""

    def __init__(self, code: str, message: str = "Không thể hoàn tất phân tích.") -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    """Tạo HTTPException theo envelope lỗi thống nhất của dự án."""
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "data": {"code": code}, "message": message},
    )


def _utcnow() -> datetime:
    """Trả thời gian UTC dạng naive để đồng bộ với cột DATETIME hiện có."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _round_score(value: float) -> Decimal:
    """Làm tròn điểm về tối đa 2 chữ số thập phân."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_ai_consent(consent: AIConsent) -> None:
    """Kiểm tra consent độc lập với frontend.

    Frontend không được xem là bằng chứng đồng ý; backend bắt buộc có
    ``accepted=True`` và đúng phiên bản mục đích được hỗ trợ.
    """
    if consent.accepted is not True:
        raise _error(
            status.HTTP_403_FORBIDDEN,
            CONSENT_REQUIRED,
            "Người dùng chưa đồng ý cho phép sử dụng dữ liệu cho AI.",
        )
    if consent.purpose_version != SUPPORTED_PURPOSE_VERSION:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            CONSENT_VERSION_UNSUPPORTED,
            "Phiên bản mục đích consent không hợp lệ hoặc không được hỗ trợ.",
        )


def get_owned_active_cv(db: Session, *, user_id: int, cv_id: int) -> CV:
    """Lấy CV đang hoạt động và kiểm tra quyền sở hữu."""
    cv = db.scalar(select(CV).where(CV.id == cv_id))
    if cv is None or not cv.is_active:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            CV_NOT_FOUND,
            "Không tìm thấy CV hoặc CV không khả dụng.",
        )
    if cv.user_id != user_id:
        raise _error(
            status.HTTP_403_FORBIDDEN,
            CV_FORBIDDEN,
            "Bạn không có quyền sử dụng CV này.",
        )
    return cv


def _load_active_role(db: Session, career_role_id: int) -> CareerRole:
    """Lấy vị trí đang hoạt động cùng bộ kỹ năng yêu cầu."""
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
            ROLE_SKILLS_REQUIRED,
            "Vị trí nghề nghiệp chưa có kỹ năng yêu cầu để phân tích.",
        )
    return role


def _skill_contexts(role: CareerRole) -> list[SkillAnalysisContext]:
    """Chuyển kỹ năng của vị trí thành dữ liệu tối thiểu cho prompt."""
    ordered = sorted(
        role.required_skills,
        key=lambda item: (-float(item.weight), -item.required_level, item.skill_id),
    )
    contexts: list[SkillAnalysisContext] = []
    for item in ordered:
        if item.skill is None:
            continue
        contexts.append(
            SkillAnalysisContext(
                skill_id=item.skill_id,
                name=item.skill.name,
                required_level=item.required_level,
                is_required=bool(item.is_required),
                weight=float(item.weight),
            )
        )
    return contexts


def _load_profile(db: Session, user_id: int) -> StudentProfile | None:
    """Lấy hồ sơ khai báo cùng điểm mạnh và kỹ năng tự đánh giá."""
    return db.scalar(
        select(StudentProfile)
        .options(
            selectinload(StudentProfile.strength_items),
            selectinload(StudentProfile.skill_assessments).joinedload(
                ProfileSkill.skill
            ),
        )
        .where(StudentProfile.user_id == user_id)
    )


def _profile_summary(profile: StudentProfile | None) -> str:
    """Dựng mô tả hồ sơ, không đưa họ tên hay email vào prompt."""
    if profile is None:
        return build_profile_summary(
            major=None,
            university=None,
            career_goal=None,
            bio=None,
            strengths=[],
            self_assessed_skills=[],
        )
    self_assessed = [
        (item.skill.name, item.level)
        for item in profile.skill_assessments
        if item.skill is not None
    ]
    return build_profile_summary(
        major=profile.major,
        university=profile.university,
        career_goal=profile.career_goal,
        bio=profile.bio,
        strengths=[item.strength for item in profile.strength_items],
        self_assessed_skills=self_assessed,
    )


def _calculate_readiness(
    *,
    current_level: int,
    required_level: int,
    weight: float,
) -> float:
    """Tính tỉ lệ đáp ứng của một kỹ năng theo công thức SRS 6.3."""
    if required_level <= 0:
        ratio = 1.0
    else:
        ratio = min(current_level / required_level, 1.0)
    return weight * ratio


def _validate_ai_assessments(
    result: SkillGapAnalysisAI,
    expected_skill_ids: set[int],
) -> None:
    """Bảo đảm AI trả đúng một đánh giá cho mỗi kỹ năng yêu cầu."""
    seen: set[int] = set()
    for item in result.assessments:
        if item.skill_id not in expected_skill_ids:
            raise AnalysisPipelineError(
                INVALID_AI_RESULT,
                "AI trả về kỹ năng không thuộc vị trí mục tiêu.",
            )
        if item.skill_id in seen:
            raise AnalysisPipelineError(
                INVALID_AI_RESULT,
                "AI trả về đánh giá trùng cho cùng một kỹ năng.",
            )
        seen.add(item.skill_id)
    if seen != expected_skill_ids:
        raise AnalysisPipelineError(
            INVALID_AI_RESULT,
            "AI không trả đủ đánh giá cho toàn bộ kỹ năng yêu cầu.",
        )


def _map_ai_failure_reason(exc: AIServiceError) -> str:
    """Chuyển lỗi AI thành mã lỗi an toàn để lưu vào báo cáo."""
    if isinstance(exc, AITimeoutError):
        return "AI_TIMEOUT"
    if isinstance(exc, AIRateLimitError):
        return "AI_RATE_LIMITED"
    if isinstance(exc, AIAuthenticationError):
        return "AI_AUTHENTICATION_FAILED"
    if isinstance(exc, AIInvalidRequestError):
        return "AI_INVALID_REQUEST"
    if isinstance(exc, AIConfigurationError):
        return "AI_UNAVAILABLE"
    if isinstance(exc, AIResponseValidationError):
        return "AI_INVALID_RESPONSE"
    if isinstance(exc, AIProviderError):
        return "AI_UNAVAILABLE"
    return "AI_UNKNOWN_ERROR"


def create_analysis(
    db: Session,
    *,
    user_id: int,
    cv_id: int | None,
    career_role_id: int,
    consent: AIConsent,
) -> Analysis:
    """Kiểm tra đầu vào và tạo báo cáo ở trạng thái ``processing``.

    Hàm chỉ tạo báo cáo, chưa gọi AI. Router sẽ đăng ký tác vụ nền sau khi
    nhận được ``analysis_id``.
    """
    # 1) Consent gate phải chạy trước mọi truy vấn dữ liệu người dùng.
    validate_ai_consent(consent)

    # 2) Quyền sở hữu CV và tính hợp lệ của vị trí mục tiêu.
    if cv_id is not None:
        get_owned_active_cv(db, user_id=user_id, cv_id=cv_id)
    role = _load_active_role(db, career_role_id)

    analysis = Analysis(
        user_id=user_id,
        cv_id=cv_id,
        career_role_id=role.id,
        consent_accepted=True,
        consent_purpose_version=consent.purpose_version,
        status="processing",
    )
    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Không tạo được báo cáo phân tích.")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            DATABASE_ERROR,
            "Không thể tạo yêu cầu phân tích. Vui lòng thử lại.",
        ) from exc
    return analysis


def get_analysis_for_user(db: Session, *, analysis_id: int, user_id: int) -> Analysis:
    """Lấy báo cáo thuộc đúng người dùng hiện tại."""
    analysis = db.scalar(
        select(Analysis)
        .options(
            joinedload(Analysis.career_role),
            selectinload(Analysis.skill_gaps).joinedload(AnalysisSkillGap.skill),
        )
        .where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    )
    if analysis is None:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            ANALYSIS_NOT_FOUND,
            "Không tìm thấy báo cáo phân tích.",
        )
    return analysis


def list_analyses_for_user(
    db: Session,
    *,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Analysis], int]:
    """Lấy lịch sử báo cáo mới nhất của người dùng."""
    total = db.scalar(
        select(func.count(Analysis.id)).where(Analysis.user_id == user_id)
    ) or 0
    analyses = list(
        db.scalars(
            select(Analysis)
            .options(joinedload(Analysis.career_role))
            .where(Analysis.user_id == user_id)
            .order_by(Analysis.created_at.desc(), Analysis.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return analyses, int(total)


def list_analysis_skill_gaps(
    db: Session,
    *,
    analysis_id: int,
    user_id: int,
) -> list[AnalysisSkillGap]:
    """Lấy điểm từng kỹ năng của báo cáo thuộc người dùng hiện tại."""
    analysis = get_analysis_for_user(db, analysis_id=analysis_id, user_id=user_id)
    return list(analysis.skill_gaps)


async def run_analysis_pipeline(analysis_id: int) -> None:
    """Tác vụ nền: gọi AI và lưu kết quả phân tích.

    Luôn tự mở session riêng và không ném exception ra ngoài để lỗi nền
    không ảnh hưởng response 202 đã trả cho Client.
    """
    db = _session_factory()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None or analysis.status != "processing":
            return

        try:
            await _execute_analysis(db, analysis)
        except AIServiceError as exc:
            db.rollback()
            logger.warning(
                "Phân tích %s thất bại do lỗi AI %s.", analysis_id, exc.code
            )
            _mark_analysis_failed(db, analysis_id, _map_ai_failure_reason(exc))
        except AnalysisPipelineError as exc:
            db.rollback()
            logger.warning("Phân tích %s thất bại: %s.", analysis_id, exc.code)
            _mark_analysis_failed(db, analysis_id, exc.code)
        except Exception:  # noqa: BLE001 - tác vụ nền phải tự bảo vệ
            db.rollback()
            logger.exception("Lỗi không xác định khi phân tích %s.", analysis_id)
            _mark_analysis_failed(db, analysis_id, "ANALYSIS_INTERNAL_ERROR")
    finally:
        db.close()


async def _execute_analysis(db: Session, analysis: Analysis) -> None:
    """Thực hiện toàn bộ phép tính và ghi kết quả trong một transaction."""
    if analysis.career_role_id is None:
        raise AnalysisPipelineError(INVALID_AI_RESULT, "Báo cáo thiếu vị trí mục tiêu.")

    role = _load_active_role(db, analysis.career_role_id)
    contexts = _skill_contexts(role)
    if not contexts:
        raise AnalysisPipelineError(
            ROLE_SKILLS_REQUIRED,
            "Vị trí mục tiêu không còn kỹ năng để phân tích.",
        )

    cv_text = analysis.cv.extracted_text if analysis.cv is not None else None
    profile = _load_profile(db, analysis.user_id)

    prompt = build_skill_gap_prompt(
        career_role_name=role.name,
        career_role_level=role.level,
        career_role_description=role.description,
        skills=contexts,
        cv_text=cv_text,
        profile_summary=_profile_summary(profile),
    )

    service = get_ai_service()
    result = await service.generate_structured(
        prompt=prompt,
        response_schema=SkillGapAnalysisAI,
        system_instruction=SKILL_GAP_SYSTEM_INSTRUCTION,
    )

    expected_ids = {context.skill_id for context in contexts}
    _validate_ai_assessments(result, expected_ids)

    by_skill_id = {item.skill_id: item for item in result.assessments}
    required_by_skill = {
        item.skill_id: item for item in role.required_skills if item.skill is not None
    }

    total_weight = 0.0
    weighted_ratio = 0.0
    gaps: list[AnalysisSkillGap] = []

    for context in contexts:
        role_skill: CareerRoleSkill = required_by_skill[context.skill_id]
        assessment = by_skill_id[context.skill_id]

        # Kỹ năng không có bằng chứng luôn được tính ở mức 0 theo FR-ANA-07.
        current_level = assessment.current_level if assessment.has_evidence else 0
        required_level = role_skill.required_level
        weight = float(role_skill.weight)
        if weight <= 0:
            raise AnalysisPipelineError(
                INVALID_AI_RESULT,
                "Trọng số kỹ năng không hợp lệ.",
            )

        gap_score = max(0, required_level - current_level)
        total_weight += weight
        weighted_ratio += _calculate_readiness(
            current_level=current_level,
            required_level=required_level,
            weight=weight,
        )

        gaps.append(
            AnalysisSkillGap(
                analysis_id=analysis.id,
                skill_id=context.skill_id,
                current_level=current_level,
                required_level=required_level,
                gap_score=_round_score(gap_score),
                has_evidence=assessment.has_evidence,
                evidence=assessment.evidence,
                recommendation=assessment.recommendation,
            )
        )

    if total_weight <= 0:
        raise AnalysisPipelineError(
            INVALID_AI_RESULT,
            "Tổng trọng số kỹ năng phải lớn hơn 0.",
        )

    readiness = min(max((weighted_ratio / total_weight) * 100.0, 0.0), 100.0)

    # Ghi toàn bộ kết quả và chuyển completed trong cùng một transaction.
    try:
        db.add_all(gaps)
        analysis.readiness_score = _round_score(readiness)
        analysis.summary = result.summary
        analysis.market_source = MARKET_SOURCE
        analysis.benchmark_date = date.today()
        analysis.status = "completed"
        analysis.completed_at = _utcnow()
        analysis.failure_reason = None
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def _mark_analysis_failed(db: Session, analysis_id: int, reason: str) -> None:
    """Đánh dấu báo cáo thất bại trong transaction mới, không che giấu lỗi gốc."""
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            return
        analysis.status = "failed"
        analysis.failure_reason = reason
        analysis.completed_at = _utcnow()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Không cập nhật được trạng thái thất bại cho phân tích %s.", analysis_id)
