from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.analysis import AnalysisGateError, AnalysisRequest
from app.services.analysis_service import prepare_analysis

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


@router.post(
    "",
    responses={501: {"model": AnalysisGateError, "description": "Consent valid but AI pipeline not implemented"}},
)
def create_analysis(payload: AnalysisRequest, current_user: CurrentUser, db: DbSession):
    # Consent + ownership checks are enforced in the service (independent of frontend).
    # user_id is taken from the authenticated token; never from client input.
    raise prepare_analysis(
        db,
        user_id=current_user.id,
        cv_id=payload.cv_id,
        career_role_id=payload.career_role_id,
        consent=payload.ai_consent,
    )
