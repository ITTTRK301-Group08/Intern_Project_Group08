from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Career Mentor & Skill Gap Analyzer"
    environment: str = "development"
    database_url: str = "mysql+pymysql://root:123456789@localhost:3306/ai_career_mentor"
    secret_key: str = "CHANGE_ME_SET_SECRET_KEY_IN_ENV"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
