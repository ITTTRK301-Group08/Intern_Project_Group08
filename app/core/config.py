import secrets
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Career Mentor & Skill Gap Analyzer"
    environment: str = "development"
    database_url: str = "mysql+pymysql://root:123456789@localhost:3306/ai_career_mentor"
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)
    cors_allowed_origins: list[str] = Field(default_factory=list)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized.encode("utf-8")) < 32 or normalized.casefold().startswith(
            ("change-me", "changeme", "replace-me", "your-secret")
        ):
            raise ValueError("SECRET_KEY must be a private random value of at least 32 bytes")
        return normalized

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        normalized: list[str] = []
        for origin in origins:
            origin = origin.strip().rstrip("/")
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in origin
            ):
                raise ValueError(f"Invalid CORS origin: {origin!r}")
            if origin not in normalized:
                normalized.append(origin)
        return normalized

    @model_validator(mode="after")
    def require_explicit_production_secret(self) -> "Settings":
        if (
            self.environment.casefold() in {"production", "prod"}
            and "secret_key" not in self.model_fields_set
        ):
            raise ValueError("SECRET_KEY must be explicitly configured in production")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
