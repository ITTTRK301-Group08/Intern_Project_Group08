from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RegisterData,
    RegisterRequest,
    RegisterResponse,
    TokenData,
)
from app.schemas.user import UserResponse
from app.services.auth_service import authenticate_user, register_user

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
    _user, access_token = authenticate_user(db, payload)
    return LoginResponse(
        data=TokenData(access_token=access_token, token_type="bearer"),
        message="Login successful",
    )


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser) -> MeResponse:
    return MeResponse(
        data=UserResponse.model_validate(current_user),
        message="Current user retrieved",
    )
