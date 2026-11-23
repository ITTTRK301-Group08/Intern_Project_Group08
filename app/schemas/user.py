from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserRead(BaseModel):
    """Thông tin người dùng hiển thị trong trang quản trị.

    Không chứa ``password_hash`` hay bất kỳ dữ liệu phiên đăng nhập nào.
    ``full_name`` được lấy từ ``student_profiles`` (có thể ``None`` nếu tài
    khoản chưa hoàn thiện hồ sơ).
    """

    id: int
    email: EmailStr
    full_name: str | None = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class AdminUserProfileRead(BaseModel):
    full_name: str | None = None
    major: str | None = None
    university: str | None = None
    career_goal: str | None = None
    target_role_name: str | None = None


class AdminUserDetailRead(AdminUserRead):
    profile: AdminUserProfileRead | None = None
    total_analyses: int = 0
    total_interviews: int = 0
