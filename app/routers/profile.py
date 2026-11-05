from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.profile import ProfileApiResponse, ProfileUpdateRequest
from app.services.profile_service import get_profile_by_user_id, update_profile

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("/me", response_model=ProfileApiResponse)
def get_my_profile(current_user: CurrentUser, db: DbSession) -> ProfileApiResponse:
    profile = get_profile_by_user_id(db, current_user.id, email=current_user.email)
    return ProfileApiResponse(data=profile, message="Lay ho so thanh cong")


@router.put("/me", response_model=ProfileApiResponse)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ProfileApiResponse:
    profile = update_profile(db, current_user.id, payload, email=current_user.email)
    return ProfileApiResponse(data=profile, message="Cap nhat ho so thanh cong")
