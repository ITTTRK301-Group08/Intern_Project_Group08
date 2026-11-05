from typing import Any, Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterData(BaseModel):
    user: UserResponse


RegisterResponse = ApiResponse[RegisterData]
LoginResponse = ApiResponse[TokenData]
MeResponse = ApiResponse[UserResponse]
ErrorResponse = ApiResponse[dict[str, Any] | None]
