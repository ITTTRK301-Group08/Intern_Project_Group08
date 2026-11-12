import logging
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database.connection import SessionLocal
from app.models.analysis import Analysis, AnalysisSkillGap
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

CONSENT_REQUIRED = "AI_CONSENT_REQUIRED"
CONSENT_VERSION_UNSUPPORTED = "AI_CONSENT_VERSION_UNSUPPORTED"
CV_NOT_FOUND = "CV_NOT_FOUND"
CV_FORBIDDEN = "CV_FORBIDDEN"
CV_NO_EXTRACTABLE_TEXT = "CV_NO_EXTRACTABLE_TEXT"
CAREER_ROLE_NOT_FOUND = "CAREER_ROLE_NOT_FOUND"
CAREER_ROLE_HAS_NO_SKILLS = "CAREER_ROLE_HAS_NO_SKILLS"
ANALYSIS_SOURCE_REQUIRED = "ANALYSIS_SOURCE_REQUIRED"
ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "data": {"code": code}, "message": message},
    )


def validate_ai_consent(consent: AIConsent) -> None:
    """Validate consent independently of frontend checks.

    Frontend metadata is not trusted as proof of consent; backend enforces
    explicit acceptance and a server-supported purpose version.
    """
    if consent.accepted is not True:
        raise _error(
            status.HTTP_403_FORBIDDEN,
            CONSENT_REQUIRED,
            "Nguoi dung chua dong y xu ly du lieu de phan tich.",
        )
    if consent.purpose_version != SUPPORTED_PURPOSE_VERSION:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            CONSENT_VERSION_UNSUPPORTED,
            "Phien ban muc dich consent khong hop le hoac khong duoc ho tro.",
        )


def get_owned_active_cv(db: Session, *, user_id: int, cv_id: int) -> CV:
    cv = db.scalar(select(CV).where(CV.id == cv_id))
    if cv is None or not cv.is_active:
        raise _error(status.HTTP_404_NOT_FOUND, CV_NOT_FOUND, "Khong tim thay CV hoac CV khong kha dung.")
    if cv.user_id != user_id:
        raise _error(status.HTTP_403_FORBIDDEN, CV_FORBIDDEN, "Ban khong co quyen su dung CV nay.")
    return cv


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
        )
    if not role.required_skills:
        raise _error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            CAREER_ROLE_HAS_NO_SKILLS,
            "Vi tri nghe nghiep chua co ky nang muc tieu de phan tich.",
        )
    return role


def create_analysis(
    db: Session,
    *,
    user_id: int,
    cv_id: int | None,
    career_role_id: int,
    consent: AIConsent,
) -> Analysis:
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
    )
