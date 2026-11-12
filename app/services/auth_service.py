import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest


def register_user(db: Session, payload: RegisterRequest) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="student",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error") from exc
    db.refresh(user)
    return user


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def _commit_session_change(db: Session, message: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message,
        ) from exc


def _unauthorized_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token is invalid or expired",
    )


def authenticate_user(db: Session, payload: LoginRequest) -> tuple[User, str, str]:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    refresh_token = _new_refresh_token()
    now = _utcnow()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            family_id=str(uuid4()),
            expires_at=now
            + timedelta(days=get_settings().refresh_token_expire_days),
        )
    )
    _commit_session_change(db, "Could not create session")
    access_token = create_access_token({"sub": str(user.id)})
    return user, access_token, refresh_token


def refresh_session(db: Session, payload: RefreshRequest) -> tuple[str, str]:
    token_hash = hash_refresh_token(payload.refresh_token)
    current = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    if current is None:
        raise _unauthorized_refresh()

    now = _utcnow()
    if current.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == current.family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        _commit_session_change(db, "Could not revoke reused session")
        raise _unauthorized_refresh()
    if current.expires_at <= now:
        current.revoked_at = now
        _commit_session_change(db, "Could not expire session")
        raise _unauthorized_refresh()

    user = db.get(User, current.user_id)
    if user is None or not user.is_active:
        current.revoked_at = now
        _commit_session_change(db, "Could not revoke inactive session")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired",
        )

    refresh_token = _new_refresh_token()
    current.revoked_at = now
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            family_id=current.family_id,
            expires_at=now
            + timedelta(days=get_settings().refresh_token_expire_days),
        )
    )
    access_token = create_access_token({"sub": str(user.id)})
    _commit_session_change(db, "Could not refresh session")
    return access_token, refresh_token


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(refresh_token)
        )
    )
    if token is not None and token.revoked_at is None:
        token.revoked_at = _utcnow()
        _commit_session_change(db, "Could not revoke session")
