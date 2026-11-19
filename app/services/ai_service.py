"""Điểm tích hợp AI dùng chung (giữ tên module cũ để tương thích ngược).

Các module Sprint 1 đang import `app.services.ai_service`; module này tái xuất
toàn bộ thành phần của package `app.services.ai` và giữ nguyên điểm vào
`request_skill_gap_analysis`. Pipeline nghiệp vụ thực tế sẽ được triển khai ở
task sau và phải gọi `AIService` thay vì gọi SDK trực tiếp.
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
    """Điểm vào cũ của luồng phân tích Skill Gap (chưa triển khai).

    Task 1 chỉ xây dựng hạ tầng AI dùng chung. Logic nghiệp vụ Skill Gap sẽ
    được triển khai ở task riêng và phải sử dụng `AIService` để bảo đảm dữ liệu
    đầu ra luôn được xác thực.
    """
    raise NotImplementedError(
        "AI analysis pipeline is not implemented (Task 4 consent gate only)"
    )
