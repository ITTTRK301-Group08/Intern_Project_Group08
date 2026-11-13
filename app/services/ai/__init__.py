"""Package dịch vụ AI dùng chung của backend.

Các module nghiệp vụ chỉ nên phụ thuộc vào `AIService` và các exception trong
package này, không gọi trực tiếp SDK của nhà cung cấp AI.
"""

from app.services.ai.ai_factory import SUPPORTED_PROVIDERS, create_ai_provider
from app.services.ai.ai_service import AIService, create_ai_service, get_ai_service
from app.services.ai.base import BaseAIProvider
from app.services.ai.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AIServiceError,
    AITimeoutError,
)
from app.services.ai.gemini_provider import GeminiProvider

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
]
