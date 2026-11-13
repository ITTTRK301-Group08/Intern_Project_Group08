from fastapi import APIRouter, File, Path, Query, UploadFile, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.cv import (
    CVDeleteResponse,
    CVDetailData,
    CVDetailResponse,
    CVListData,
    CVListResponse,
    CVUploadData,
    CVUploadResponse,
)
from app.services.cv_service import (
    build_cv_extraction_warning,
    delete_user_cv,
    get_user_cv_detail,
    list_user_cvs,
    serialize_cv_response,
    upload_cv,
)

router = APIRouter(prefix="/api/v1/cvs", tags=["cvs"])


@router.post("", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_my_cv(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> CVUploadResponse:
    cv, has_text = upload_cv(db, current_user.id, file)
    cv_data = serialize_cv_response(cv, analysis_count=0)
    warning = None if has_text else build_cv_extraction_warning(cv)
    message = "Upload CV thanh cong"
    if not has_text:
        message = (
            "Upload CV thanh cong nhung khong trich xuat duoc noi dung van ban "
            "(co the file PDF la anh quet khong co lop van ban). "
            "Vui long kiem tra file hoac cap nhat ho so de phan tich tu du lieu ho so khai bao."
        )
    return CVUploadResponse(
        data=CVUploadData(cv=cv_data, has_text=has_text, warning=warning),
        message=message,
    )


@router.get("", response_model=CVListResponse)
def list_my_cvs(
    current_user: CurrentUser,
    db: DbSession,
    include_inactive: bool = Query(default=False),
) -> CVListResponse:
    cvs = list_user_cvs(db, current_user.id, include_inactive=include_inactive)
    return CVListResponse(
        data=CVListData(cvs=cvs, total=len(cvs)),
        message="Lay danh sach CV thanh cong",
    )


@router.get("/{cv_id}", response_model=CVDetailResponse)
def get_my_cv_detail(
    current_user: CurrentUser,
    db: DbSession,
    cv_id: int = Path(gt=0),
    include_inactive: bool = Query(default=False),
) -> CVDetailResponse:
    cv_data, warning = get_user_cv_detail(
        db, current_user.id, cv_id, include_inactive=include_inactive
    )
    return CVDetailResponse(
        data=CVDetailData(cv=cv_data, warning=warning),
        message="Lay chi tiet CV thanh cong",
    )


@router.delete("/{cv_id}", response_model=CVDeleteResponse)
def delete_my_cv(
    current_user: CurrentUser,
    db: DbSession,
    cv_id: int = Path(gt=0),
) -> CVDeleteResponse:
    result, message = delete_user_cv(db, current_user.id, cv_id)
    return CVDeleteResponse(data=result, message=message)
