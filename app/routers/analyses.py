from fastapi import APIRouter, BackgroundTasks, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.analysis import (
    AnalysisAcceptedData,
    AnalysisAcceptedResponse,
    AnalysisRequest,
    AnalysisResultResponse,
)
from app.services.analysis_service import (
    create_analysis,
    get_analysis_result,
    process_analysis,
)

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


@router.post(
    "",
    response_model=AnalysisAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_analysis(
    payload: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
) -> AnalysisAcceptedResponse:
    analysis = create_analysis(
        db,
        user_id=current_user.id,
        cv_id=payload.cv_id,
        career_role_id=payload.career_role_id,
        consent=payload.ai_consent,
    )
    background_tasks.add_task(process_analysis, analysis.id)
    return AnalysisAcceptedResponse(
        data=AnalysisAcceptedData(
            id=analysis.id,
            status="pending",
            status_url=f"/api/v1/analyses/{analysis.id}",
        ),
        message="Yeu cau phan tich da duoc tiep nhan.",
    )


@router.get("/{analysis_id}", response_model=AnalysisResultResponse)
def read_analysis(
    analysis_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> AnalysisResultResponse:
    result = get_analysis_result(
        db, analysis_id=analysis_id, user_id=current_user.id
    )
    return AnalysisResultResponse(
        data=result,
        message=(
            "Phan tich da hoan tat."
            if result.status == "completed"
            else "Trang thai phan tich da duoc cap nhat."
        ),
    )
