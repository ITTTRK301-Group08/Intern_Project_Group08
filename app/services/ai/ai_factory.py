"""Factory khởi tạo nhà cung cấp AI theo cấu hình của ứng dụng."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.exceptions import AIConfigurationError
from app.services.ai.gemini_provider import GeminiProvider

# Danh sách provider đang được hỗ trợ. Bổ sung tại đây khi tích hợp provider mới.
SUPPORTED_PROVIDERS: tuple[str, ...] = ("gemini",)


def create_ai_provider(settings: Settings | None = None) -> BaseAIProvider:
    """Tạo provider tương ứng với `AI_PROVIDER`.

    Nếu provider không được hỗ trợ, trả lỗi cấu hình rõ ràng thay vì tạo một
    provider giả để che giấu sai sót.
    """
    configured = settings or get_settings()
    provider_name = (configured.ai_provider or "").strip().casefold()

    if provider_name not in SUPPORTED_PROVIDERS:
        raise AIConfigurationError(
            f"AI_PROVIDER không được hỗ trợ: {provider_name!r}. Giá trị hợp lệ: gemini."
        )

    if provider_name == "gemini":
        return GeminiProvider(
            api_key=configured.gemini_api_key.get_secret_value(),
            model=configured.gemini_model,
            timeout=configured.ai_timeout,
        )

    # Nhánh này chỉ xảy ra nếu SUPPORTED_PROVIDERS được mở rộng mà quên cập nhật.
    raise AIConfigurationError(
        f"Chưa có triển khai cho AI_PROVIDER={provider_name!r}.",
        provider=provider_name,
    )
