import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cv import CV
from app.schemas.analysis import SUPPORTED_PURPOSE_VERSION, AIConsent
from app.services import ai_service

logger = logging.getLogger(__name__)

ANALYSIS_PIPELINE_NOT_IMPLEMENTED = "ANALYSIS_PIPELINE_NOT_IMPLEMENTED"
CONSENT_REQUIRED = "AI_CONSENT_REQUIRED"
CONSENT_VERSION_UNSUPPORTED = "AI_CONSENT_VERSION_UNSUPPORTED"
CV_NOT_FOUND = "CV_NOT_FOUND"
CV_FORBIDDEN = "CV_FORBIDDEN"


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

    # 3) Only minimal, necessary identifiers reach the AI boundary; never auth data.
    # Task 4 does NOT call any AI provider and does NOT fabricate analysis results.
    _ = (user_id, cv_id, career_role_id, ai_service)  # integration point retained; unused in Task 4
    logger.info("AI consent validated for analysis request (no AI call performed)")

    return _error(
        status.HTTP_501_NOT_IMPLEMENTED,
        ANALYSIS_PIPELINE_NOT_IMPLEMENTED,
        "Da xac nhan consent hop le, nhung pipeline phan tich AI (M4) chua duoc trien khai trong Task 4.",
    )
