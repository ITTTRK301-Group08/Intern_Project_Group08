from fastapi import APIRouter, File, UploadFile, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.cv import CVResponse, CVUploadData, CVUploadResponse
from app.services.cv_service import upload_cv

router = APIRouter(prefix="/api/v1/cvs", tags=["cvs"])


@router.post("", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_my_cv(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> CVUploadResponse:
    cv, has_text = upload_cv(db, current_user.id, file)
    message = "Upload CV thanh cong"
    if not has_text:
        message = "Upload CV thanh cong nhung khong trich xuat duoc noi dung van ban. Vui long kiem tra file hoac cap nhat ho so."
    return CVUploadResponse(data=CVUploadData(cv=CVResponse.model_validate(cv)), message=message)
