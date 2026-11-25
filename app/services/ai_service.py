"""Điểm tích hợp AI dùng chung, giữ tên module cũ để tương thích ngược.

Pipeline báo cáo hiện chạy trong `analysis_service` qua `AIService`; các module
nghiệp vụ không gọi trực tiếp SDK. Hàm cũ vẫn được giữ cho import tương thích.
"""

from datetime import datetime
from typing import TypedDict

from app.services.ai import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AIService,
    AIServiceError,
    AITimeoutError,
    BaseAIProvider,
    GeminiProvider,
    SUPPORTED_PROVIDERS,
    create_ai_provider,
    create_ai_service,
    get_ai_service,
)


class ProfileAnalysisContext(TypedDict):
    """Du lieu ho so hoc sinh da xac thuc cho pipeline phan tich AI."""

    strengths: list[str]
    self_assessed_skills: list[dict[str, str | int]]
    career_goal: str | None
    bio: str | None
    profile_updated_at: datetime


__all__ = [
    "AIAuthenticationError",
    "AIConfigurationError",
    "AIInvalidRequestError",
    "AIProviderError",
    "AIRateLimitError",
    "AIResponseValidationError",
    "AIService",
    "AIServiceError",
    "AITimeoutError",
    "BaseAIProvider",
    "GeminiProvider",
    "SUPPORTED_PROVIDERS",
    "create_ai_provider",
    "create_ai_service",
    "get_ai_service",
    "ProfileAnalysisContext",
    "request_skill_gap_analysis",
]


def request_skill_gap_analysis(
    *, user_id: int, cv_id: int | None, career_role_id: int | None
) -> None:
    """Entry point cũ không còn được dùng; cần phiên đăng nhập và session DB."""
    raise NotImplementedError(
        "Use the authenticated POST /api/v1/analyses endpoint instead."
    )
