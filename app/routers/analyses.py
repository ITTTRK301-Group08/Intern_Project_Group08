from math import ceil

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.analysis import (
    AnalysisGateError,
    AnalysisHistoryData,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    AnalysisReport,
    AnalysisReportResponse,
    AnalysisRequest,
    AnalysisSkillReport,
    AnalysisSkillsResponse,
    AnalysisStatusResponse,
)
from app.services.analysis_service import (
    get_user_analysis,
    get_user_analysis_skills,
    list_user_analyses,
    prepare_analysis,
)

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


@router.get("", response_model=AnalysisHistoryResponse)
def list_analyses(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> AnalysisHistoryResponse:
    analyses, total = list_user_analyses(
        db, user_id=current_user.id, page=page, page_size=page_size
    )
    items = [
        AnalysisHistoryItem(
            id=analysis.id,
            status=analysis.status,
            readiness_score=analysis.readiness_score,
            summary=analysis.summary,
            career_role_name=analysis.career_role.name if analysis.career_role else None,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
        )
        for analysis in analyses
    ]
    return AnalysisHistoryResponse(
        data=AnalysisHistoryData(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size),
        ),
        message="Lay lich su phan tich thanh cong",
    )


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(
    analysis_id: int, current_user: CurrentUser, db: DbSession
) -> AnalysisStatusResponse:
    analysis = get_user_analysis(
        db, user_id=current_user.id, analysis_id=analysis_id
    )
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )
    return AnalysisStatusResponse(
        data={"status": analysis.status},
        message="Lay trang thai phan tich thanh cong",
    )


@router.get("/{analysis_id}/skills", response_model=AnalysisSkillsResponse)
def get_analysis_skills(
    analysis_id: int, current_user: CurrentUser, db: DbSession
) -> AnalysisSkillsResponse:
    skill_gaps = get_user_analysis_skills(
        db, user_id=current_user.id, analysis_id=analysis_id
    )
    if skill_gaps is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )
    skills = [
        AnalysisSkillReport(
            id=gap.id,
            skill_id=gap.skill_id,
            skill_name=skill.name,
            current_level=gap.current_level,
            required_level=gap.target_level,
            gap_score=gap.target_level - gap.current_level,
            evidence=gap.evidence,
            has_evidence=gap.has_evidence,
            recommendation=gap.recommendation,
        )
        for gap, skill in skill_gaps
    ]
    return AnalysisSkillsResponse(
        data=skills, message="Lay chi tiet ky nang thanh cong"
    )


@router.get("/{analysis_id}", response_model=AnalysisReportResponse)
def get_analysis_report(
    analysis_id: int, current_user: CurrentUser, db: DbSession
) -> AnalysisReportResponse:
    analysis = get_user_analysis(
        db, user_id=current_user.id, analysis_id=analysis_id
    )
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )
    return AnalysisReportResponse(
        data=AnalysisReport(
            id=analysis.id,
            status=analysis.status,
            readiness_score=analysis.readiness_score,
            summary=analysis.summary,
            career_role_name=analysis.career_role.name if analysis.career_role else None,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
        ),
        message="Lay bao cao phan tich thanh cong",
    )
