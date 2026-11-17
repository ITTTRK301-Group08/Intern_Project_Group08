import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings

# bcrypt truncates inputs longer than 72 bytes; enforce explicitly.
BCRYPT_MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be a string",
        )
    try:
        password_bytes = password.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be valid UTF-8",
        ) from exc
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at most 72 bytes when UTF-8 encoded",
        )
    return password_bytes


def hash_password(password: str) -> str:
    password_bytes = _password_bytes(password)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = _password_bytes(plain_password)
    except HTTPException:
        return False
    if not hashed_password:
        return False
    try:
        hashed_bytes = hashed_password.encode("utf-8")
    except (UnicodeEncodeError, AttributeError):
        return False
    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "jti": secrets.token_urlsafe(16)})
    if "sub" not in to_encode:
        raise ValueError("Token payload must include 'sub'")
    to_encode["sub"] = str(to_encode["sub"])
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
