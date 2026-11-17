import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.analysis import Analysis, AnalysisSkillGap
from app.models.career import Skill
from app.models.cv import CV
from app.models.profile_data import ProfileSkill
from app.models.student_profile import StudentProfile
from app.schemas.analysis import SUPPORTED_PURPOSE_VERSION, AIConsent
from app.services.ai_service import ProfileAnalysisContext

logger = logging.getLogger(__name__)

ANALYSIS_PIPELINE_NOT_IMPLEMENTED = "ANALYSIS_PIPELINE_NOT_IMPLEMENTED"
CONSENT_REQUIRED = "AI_CONSENT_REQUIRED"
CONSENT_VERSION_UNSUPPORTED = "AI_CONSENT_VERSION_UNSUPPORTED"
CV_NOT_FOUND = "CV_NOT_FOUND"
CV_FORBIDDEN = "CV_FORBIDDEN"
PROFILE_REQUIRED = "PROFILE_DATA_REQUIRED"


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
            "Nguoi dung chua dong y cho phep su dung du lieu cho AI.",
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


def build_profile_analysis_context(
    db: Session, *, user_id: int
) -> ProfileAnalysisContext:
    profile = db.scalar(
        select(StudentProfile)
        .options(
            selectinload(StudentProfile.strength_items),
            selectinload(StudentProfile.skill_assessments).joinedload(ProfileSkill.skill),
        )
        .where(StudentProfile.user_id == user_id)
    )
    if profile is None:
        raise _error(
            status.HTTP_400_BAD_REQUEST,
            PROFILE_REQUIRED,
            "Vui long cap nhat diem manh, ky nang tu danh gia, muc tieu nghe nghiep hoac gioi thieu ban than truoc khi phan tich.",
        )

    strengths = [strength.strip() for strength in profile.strengths if strength.strip()]
    self_assessed_skills = [
        {"skill_name": item["skill_name"].strip(), "level": item["level"]}
        for item in profile.self_assessed_skills
        if item["skill_name"].strip()
    ]
    career_goal = profile.career_goal.strip() if profile.career_goal else None
    bio = profile.bio.strip() if profile.bio else None
    if not (strengths or self_assessed_skills or career_goal or bio):
        raise _error(
            status.HTTP_400_BAD_REQUEST,
            PROFILE_REQUIRED,
            "Vui long cap nhat diem manh, ky nang tu danh gia, muc tieu nghe nghiep hoac gioi thieu ban than truoc khi phan tich.",
        )

    return {
        "strengths": strengths,
        "self_assessed_skills": self_assessed_skills,
        "career_goal": career_goal,
        "bio": bio,
        "profile_updated_at": profile.updated_at,
    }


def prepare_analysis(
    db: Session,
    *,
    user_id: int,
    cv_id: int | None,
    career_role_id: int | None,
    consent: AIConsent,
) -> HTTPException:
    # 1) Consent gate must run before any further processing.
    validate_ai_consent(consent)

    # 2) Ownership check when a CV is selected.
    if cv_id is not None:
        get_owned_active_cv(db, user_id=user_id, cv_id=cv_id)
        source = "CV"
    else:
        _profile_context = build_profile_analysis_context(db, user_id=user_id)
        source = "student_profile"

    # The validated context is ready for the AI integration, which remains disabled.
    logger.info(
        "AI consent validated for analysis request (source=%s; provider not configured)",
        source,
    )

    return _error(
        status.HTTP_501_NOT_IMPLEMENTED,
        ANALYSIS_PIPELINE_NOT_IMPLEMENTED,
        "Da xac nhan consent hop le, nhung pipeline phan tich AI (M4) chua duoc trien khai trong Task 4.",
    )


def list_user_analyses(
    db: Session, *, user_id: int, page: int, page_size: int
) -> tuple[list[Analysis], int]:
    filters = Analysis.user_id == user_id
    total = db.scalar(select(func.count(Analysis.id)).where(filters)) or 0
    analyses = db.scalars(
        select(Analysis)
        .options(joinedload(Analysis.career_role))
        .where(filters)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return analyses, total


def get_user_analysis(
    db: Session, *, user_id: int, analysis_id: int
) -> Analysis | None:
    return db.scalar(
        select(Analysis)
        .options(joinedload(Analysis.career_role))
        .where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    )


def get_user_analysis_skills(
    db: Session, *, user_id: int, analysis_id: int
) -> list[tuple[AnalysisSkillGap, Skill]] | None:
    analysis_exists = db.scalar(
        select(Analysis.id).where(
            Analysis.id == analysis_id, Analysis.user_id == user_id
        )
    )
    if analysis_exists is None:
        return None

    gaps = db.execute(
        select(AnalysisSkillGap, Skill)
        .join(Analysis, Analysis.id == AnalysisSkillGap.analysis_id)
        .join(Skill, Skill.id == AnalysisSkillGap.skill_id)
        .where(Analysis.id == analysis_id, Analysis.user_id == user_id)
        .order_by(Skill.name, AnalysisSkillGap.id)
    ).all()
    return [(gap, skill) for gap, skill in gaps]
