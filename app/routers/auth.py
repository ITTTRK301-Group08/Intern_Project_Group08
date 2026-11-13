from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutData,
    LogoutResponse,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterData,
    RegisterRequest,
    RegisterResponse,
    TokenData,
)
from app.schemas.user import UserResponse
from app.services.auth_service import (
    authenticate_user,
    refresh_session,
    register_user,
    revoke_refresh_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, db: DbSession) -> RegisterResponse:
    user = register_user(db, payload)
    return RegisterResponse(
        data=RegisterData(user=UserResponse.model_validate(user)),
        message="Registration successful",
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    _user, access_token, refresh_token = authenticate_user(db, payload)
    return LoginResponse(
        data=TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
        message="Login successful",
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest, db: DbSession) -> RefreshResponse:
    access_token, refresh_token = refresh_session(db, payload)
    return RefreshResponse(
        data=TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        ),
        message="Session refreshed",
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(payload: RefreshRequest, db: DbSession) -> LogoutResponse:
    revoke_refresh_token(db, payload.refresh_token)
    return LogoutResponse(
        data=LogoutData(),
        message="Logged out",
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(
        data=UserResponse.model_validate(current_user),
        message="Current user retrieved",
    )
