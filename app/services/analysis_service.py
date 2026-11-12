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
<<<<<<< HEAD
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
=======
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database.connection import SessionLocal
from app.models.analysis import Analysis, AnalysisSkillGap
<<<<<<< HEAD
from app.models.career import CareerRole, Skill
from app.models.cv import CV
from app.models.profile_data import CareerRoleSkill, ProfileSkill
from app.models.student_profile import StudentProfile
from app.schemas.analysis import (
    AnalysisResultData,
    AnalysisSkillGapRead,
    AIConsent,
    SUPPORTED_PURPOSE_VERSION,
)

logger = logging.getLogger(__name__)

=======
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

>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
CONSENT_REQUIRED = "AI_CONSENT_REQUIRED"
CONSENT_VERSION_UNSUPPORTED = "AI_CONSENT_VERSION_UNSUPPORTED"
CV_NOT_FOUND = "CV_NOT_FOUND"
CV_FORBIDDEN = "CV_FORBIDDEN"
<<<<<<< HEAD
CV_NO_EXTRACTABLE_TEXT = "CV_NO_EXTRACTABLE_TEXT"
CAREER_ROLE_NOT_FOUND = "CAREER_ROLE_NOT_FOUND"
CAREER_ROLE_HAS_NO_SKILLS = "CAREER_ROLE_HAS_NO_SKILLS"
ANALYSIS_SOURCE_REQUIRED = "ANALYSIS_SOURCE_REQUIRED"
ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"
=======
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
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1


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
<<<<<<< HEAD
            "Nguoi dung chua dong y xu ly du lieu de phan tich.",
=======
            "Người dùng chưa đồng ý cho phép sử dụng dữ liệu cho AI.",
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
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


<<<<<<< HEAD
def _validate_target_role(db: Session, career_role_id: int) -> CareerRole:
    role = db.scalar(
        select(CareerRole)
        .options(selectinload(CareerRole.required_skills))
        .where(CareerRole.id == career_role_id, CareerRole.is_active.is_(True))
    )
    if role is None:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            CAREER_ROLE_NOT_FOUND,
            "Khong tim thay vi tri nghe nghiep hoac vi tri khong kha dung.",
=======
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
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
        )
    if not role.required_skills:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
<<<<<<< HEAD
            CAREER_ROLE_HAS_NO_SKILLS,
            "Vi tri nghe nghiep chua co ky nang muc tieu de phan tich.",
=======
            ROLE_SKILLS_REQUIRED,
            "Vị trí nghề nghiệp chưa có kỹ năng yêu cầu để phân tích.",
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
        )
    return role


<<<<<<< HEAD
=======
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


>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
def create_analysis(
    db: Session,
    *,
    user_id: int,
    cv_id: int | None,
    career_role_id: int,
    consent: AIConsent,
) -> Analysis:
<<<<<<< HEAD
    validate_ai_consent(consent)

    cv = None
    if cv_id is not None:
        cv = get_owned_active_cv(db, user_id=user_id, cv_id=cv_id)
        if not (cv.extracted_text or "").strip():
            raise _error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                CV_NO_EXTRACTABLE_TEXT,
                "CV khong co van ban co the doc. Hay cap nhat ho so hoac chon CV khac.",
            )

    _validate_target_role(db, career_role_id)
    profile = db.scalar(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )

    if cv is None and profile is None:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            ANALYSIS_SOURCE_REQUIRED,
            "Can co ho so ca nhan hoac CV co van ban de bat dau phan tich.",
        )

    source_type = (
        "cv_and_profile"
        if cv is not None and profile is not None
        else "cv"
        if cv is not None
        else "profile"
    )
    analysis = Analysis(
        user_id=user_id,
        cv_id=cv_id,
        career_role_id=career_role_id,
        consent_accepted=True,
        consent_purpose_version=consent.purpose_version,
        source_type=source_type,
        status="pending",
    )
    db.add(analysis)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to queue skill-gap analysis")
        raise _error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "ANALYSIS_QUEUE_FAILED",
            "Khong the tiep nhan yeu cau phan tich luc nay.",
        ) from exc
    db.refresh(analysis)
    return analysis


def _mentions_skill(text: str, skill_name: str) -> bool:
    normalized_text = re.sub(r"\s+", " ", text.casefold())
    normalized_name = re.sub(r"\s+", " ", skill_name.strip().casefold())
    if not normalized_name:
        return False
    pattern = rf"(?<!\w){re.escape(normalized_name)}(?!\w)"
    return re.search(pattern, normalized_text) is not None


def calculate_readiness(
    requirements: list[CareerRoleSkill],
    *,
    profile: StudentProfile | None,
    cv_text: str | None,
) -> tuple[int, list[AnalysisSkillGap]]:
    profile_levels = (
        {item.skill_id: item.level for item in profile.skill_assessments}
        if profile is not None
        else {}
    )
    profile_text_parts = []
    if profile is not None:
        profile_text_parts.extend(
            [profile.bio or "", *(item.strength for item in profile.strength_items)]
        )
    profile_text = " ".join(profile_text_parts).casefold()
    normalized_cv_text = (cv_text or "").casefold()

    weighted_target = 0.0
    weighted_current = 0.0
    gaps: list[AnalysisSkillGap] = []
    for requirement in requirements:
        skill: Skill = requirement.skill
        target_level = requirement.required_level
        current_level = profile_levels.get(skill.id, 0)
        if _mentions_skill(normalized_cv_text, skill.name) or _mentions_skill(
            profile_text, skill.name
        ):
            current_level = max(current_level, 1)

        current_level = min(max(current_level, 0), 5)
        weight = requirement.weight
        weighted_target += target_level * weight
        weighted_current += min(current_level, target_level) * weight
        gap = max(target_level - current_level, 0)
        gaps.append(
            AnalysisSkillGap(
                skill_id=skill.id,
                current_level=current_level,
                target_level=target_level,
                gap=gap,
                is_required=requirement.is_required,
                weight=weight,
                recommendation=(
                    f"Phat trien them {gap} muc de dat muc tieu {target_level}/5."
                    if gap
                    else None
                ),
            )
        )

    readiness = (
        100
        if weighted_target == 0
        else round(weighted_current / weighted_target * 100)
    )
    return min(max(readiness, 0), 100), gaps


def process_analysis(analysis_id: int) -> None:
    try:
        with SessionLocal.begin() as db:
            analysis = db.scalar(
                select(Analysis)
                .where(Analysis.id == analysis_id)
                .with_for_update()
            )
            if analysis is None or analysis.status != "pending":
                return
            analysis.status = "running"

        with SessionLocal.begin() as db:
            analysis = db.scalar(
                select(Analysis)
                .options(
                    selectinload(Analysis.skill_gaps),
                    joinedload(Analysis.career_role)
                    .selectinload(CareerRole.required_skills)
                    .joinedload(CareerRoleSkill.skill),
                )
                .where(Analysis.id == analysis_id)
                .with_for_update()
            )
            if analysis is None or analysis.status != "running":
                return

            role = analysis.career_role
            if role is None or not role.is_active:
                raise ValueError("Target career role is no longer available")
            if not role.required_skills:
                raise ValueError("Target career role has no skills")

            profile = None
            if analysis.source_type in {"profile", "cv_and_profile"}:
                profile = db.scalar(
                    select(StudentProfile)
                    .options(
                        selectinload(StudentProfile.skill_assessments),
                        selectinload(StudentProfile.strength_items),
                    )
                    .where(StudentProfile.user_id == analysis.user_id)
                )
                if profile is None:
                    raise ValueError("Analysis profile source is no longer available")

            cv_text = None
            if analysis.source_type in {"cv", "cv_and_profile"}:
                cv = db.scalar(
                    select(CV).where(
                        CV.id == analysis.cv_id,
                        CV.user_id == analysis.user_id,
                        CV.is_active.is_(True),
                    )
                )
                if cv is None or not (cv.extracted_text or "").strip():
                    raise ValueError("Analysis CV source is no longer available")
                cv_text = cv.extracted_text

            readiness_score, skill_gaps = calculate_readiness(
                role.required_skills,
                profile=profile,
                cv_text=cv_text,
            )
            gap_count = sum(gap.current_level < gap.target_level for gap in skill_gaps)
            source_label = {
                "profile": "ho so ca nhan",
                "cv": "CV",
                "cv_and_profile": "CV va ho so ca nhan",
            }[analysis.source_type]
            analysis.readiness_score = readiness_score
            analysis.summary = (
                f"Muc san sang: {readiness_score}/100. "
                f"Con {gap_count}/{len(skill_gaps)} ky nang chua dat muc tieu, "
                f"dua tren {source_label}."
            )
            analysis.skill_gaps = skill_gaps
            analysis.status = "completed"
            analysis.completed_at = datetime.now(timezone.utc)
    except Exception:
        logger.exception("Skill-gap analysis %s failed", analysis_id)
        try:
            with SessionLocal.begin() as db:
                analysis = db.scalar(
                    select(Analysis)
                    .where(Analysis.id == analysis_id)
                    .with_for_update()
                )
                if analysis is not None and analysis.status in {"pending", "running"}:
                    analysis.status = "failed"
                    analysis.readiness_score = None
                    analysis.summary = "Khong the hoan tat phan tich. Hay thu lai sau."
                    analysis.completed_at = datetime.now(timezone.utc)
        except Exception:
            logger.exception(
                "Could not persist failed status for analysis %s", analysis_id
            )


def get_analysis_result(
    db: Session, *, analysis_id: int, user_id: int
) -> AnalysisResultData:
    analysis = db.scalar(
        select(Analysis)
        .options(
            selectinload(Analysis.skill_gaps).joinedload(AnalysisSkillGap.skill)
        )
        .where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    )
    if analysis is None:
        raise _error(
            status.HTTP_404_NOT_FOUND,
            ANALYSIS_NOT_FOUND,
            "Khong tim thay ket qua phan tich.",
        )

    return AnalysisResultData(
        id=analysis.id,
        status=analysis.status,
        source_type=analysis.source_type,
        career_role_id=analysis.career_role_id,
        readiness_score=analysis.readiness_score,
        summary=analysis.summary,
        skill_gaps=[
            AnalysisSkillGapRead(
                skill_id=item.skill_id,
                skill_name=item.skill.name,
                current_level=item.current_level,
                target_level=item.target_level,
                gap=item.gap,
                is_required=item.is_required,
                weight=item.weight,
                recommendation=item.recommendation,
            )
            for item in analysis.skill_gaps
        ],
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
=======
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
>>>>>>> 9461ae8730e80cb3e3b53d66094fa669388a2cb1
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
