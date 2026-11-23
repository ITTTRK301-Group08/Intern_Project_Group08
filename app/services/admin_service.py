"""Truy vấn phục vụ module Admin quản lý người dùng.

Chỉ đọc dữ liệu; không chứa ``password_hash`` hay thông tin phiên đăng nhập.
"""

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.analysis import Analysis
from app.models.interview import InterviewSession
from app.models.student_profile import StudentProfile
from app.models.user import User


def _page_meta(total: int, page: int, page_size: int) -> dict[str, int]:
    total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def list_admin_users(
    db: Session,
    *,
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(
            or_(User.email.ilike(term), StudentProfile.full_name.ilike(term))
        )
    if role:
        conditions.append(User.role == role)
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))

    total_query = (
        select(func.count(User.id))
        .select_from(User)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
    )
    if conditions:
        total_query = total_query.where(*conditions)
    total = db.scalar(total_query) or 0

    query = (
        select(User, StudentProfile.full_name)
        .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
        .order_by(User.id)
        .offset(max(0, (page - 1) * page_size))
        .limit(page_size)
    )
    if conditions:
        query = query.where(*conditions)

    rows = db.execute(query).all()
    items = [
        {
            "id": user.id,
            "email": user.email,
            "full_name": full_name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        for user, full_name in rows
    ]
    return {"items": items, **_page_meta(total, page, page_size)}


def get_admin_user_detail(db: Session, user_id: int) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    profile = db.scalar(
        select(StudentProfile)
        .options(joinedload(StudentProfile.target_role))
        .where(StudentProfile.user_id == user_id)
    )
    total_analyses = (
        db.scalar(select(func.count(Analysis.id)).where(Analysis.user_id == user_id))
        or 0
    )
    total_interviews = (
        db.scalar(
            select(func.count(InterviewSession.id)).where(
                InterviewSession.user_id == user_id
            )
        )
        or 0
    )

    profile_data = None
    if profile is not None:
        profile_data = {
            "full_name": profile.full_name,
            "major": profile.major,
            "university": profile.university,
            "career_goal": profile.career_goal,
            "target_role_name": (
                profile.target_role.name
                if profile.target_role is not None
                else None
            ),
        }

    return {
        "id": user.id,
        "email": user.email,
        "full_name": profile.full_name if profile is not None else None,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "profile": profile_data,
        "total_analyses": total_analyses,
        "total_interviews": total_interviews,
    }
