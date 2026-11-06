from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.career import Skill
from app.models.profile_data import ProfileSkill, ProfileStrength
from app.models.student_profile import StudentProfile
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest


def _profile_to_response(profile: StudentProfile, email: str | None = None) -> ProfileResponse:
    data = ProfileResponse.model_validate(profile)
    if email is not None:
        data.email = email
    return data


def get_profile_by_user_id(db: Session, user_id: int, email: str | None = None) -> ProfileResponse:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return _profile_to_response(profile, email=email)


def update_profile(
    db: Session,
    user_id: int,
    payload: ProfileUpdateRequest,
    email: str | None = None,
) -> ProfileResponse:
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))

    # Only apply fields explicitly provided by the client to avoid accidental overwrites.
    provided = payload.model_fields_set
    values = payload.model_dump(exclude_unset=True)

    if profile is None:
        if "full_name" not in provided:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="full_name is required when creating a profile",
            )
        profile = StudentProfile(user_id=user_id, full_name=values["full_name"])
        db.add(profile)
        provided = provided - {"full_name"}

    for field in provided:
        if field == "strengths":
            profile.strength_items = [
                ProfileStrength(strength=strength)
                for strength in values.get(field) or []
            ]
        elif field == "self_assessed_skills":
            skills_by_name: dict[str, tuple[Skill, int]] = {}
            for assessment in payload.self_assessed_skills or []:
                skill_name = assessment.skill_name.strip()
                normalized_name = skill_name.casefold()
                skill = db.scalar(
                    select(Skill).where(func.lower(Skill.name) == skill_name.lower())
                )
                if skill is None:
                    skill = Skill(name=skill_name)
                    db.add(skill)
                    db.flush()
                skills_by_name[normalized_name] = (skill, assessment.level)
            profile.skill_assessments = [
                ProfileSkill(skill=skill, level=level)
                for skill, level in skills_by_name.values()
            ]
        else:
            setattr(profile, field, values.get(field))

    profile.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profile already exists") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error") from exc

    db.refresh(profile)
    return _profile_to_response(profile, email=email)
