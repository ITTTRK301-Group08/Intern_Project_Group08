"""Các exception chuẩn hóa của lớp AI dùng chung.

Tầng nghiệp vụ chỉ cần bắt `AIServiceError` và phân biệt bằng `code`,
`retryable` hoặc kiểu con cụ thể. Thông điệp lỗi không bao giờ chứa API Key
hay thông tin nội bộ của SDK.
"""

from __future__ import annotations

from typing import Any


class AIServiceError(Exception):
    """Lỗi gốc cho mọi lỗi phát sinh từ lớp AI."""

    code = "AI_SERVICE_ERROR"
    default_message = "Lớp AI gặp lỗi không xác định."
    retryable = False

    def __init__(
        self,
        message: str | None = None,
        *,
        provider: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Chuyển lỗi thành cấu trúc an toàn để tầng trên sử dụng."""
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.provider:
            payload["provider"] = self.provider
        if self.retry_after is not None:
            payload["retry_after"] = self.retry_after
        return payload


class AIConfigurationError(AIServiceError):
    """Cấu hình AI thiếu, sai hoặc chưa được hỗ trợ.

    Lỗi này không thể khắc phục bằng cách gửi lại yêu cầu, nên không retry.
    """

    code = "AI_CONFIGURATION_ERROR"
    default_message = "Cấu hình AI không hợp lệ."


class AIProviderError(AIServiceError):
    """Nhà cung cấp AI gặp lỗi tạm thời (mạng, máy chủ hoặc phản hồi bất thường)."""

    code = "AI_PROVIDER_ERROR"
    default_message = "Nhà cung cấp AI gặp lỗi."
    retryable = True


class AIAuthenticationError(AIProviderError):
    """Nhà cung cấp AI từ chối xác thực API Key hoặc quyền truy cập."""

    code = "AI_AUTHENTICATION_ERROR"
    default_message = "Nhà cung cấp AI từ chối xác thực."
    retryable = False


class AIInvalidRequestError(AIProviderError):
    """Yêu cầu gửi tới nhà cung cấp AI không hợp lệ và không nên gửi lại."""

    code = "AI_INVALID_REQUEST_ERROR"
    default_message = "Yêu cầu gửi tới nhà cung cấp AI không hợp lệ."
    retryable = False


class AITimeoutError(AIServiceError):
    """Yêu cầu tới nhà cung cấp AI vượt quá thời gian chờ."""

    code = "AI_TIMEOUT_ERROR"
    default_message = "Yêu cầu tới nhà cung cấp AI đã hết thời gian chờ."
    retryable = True


class AIRateLimitError(AIServiceError):
    """Nhà cung cấp AI giới hạn tần suất hoặc hạn mức sử dụng."""

    code = "AI_RATE_LIMIT_ERROR"
    default_message = "Nhà cung cấp AI đã giới hạn số lượng yêu cầu."
    retryable = True


class AIResponseValidationError(AIServiceError):
    """Phản hồi của AI rỗng, không phải JSON hợp lệ hoặc không khớp schema."""

    code = "AI_RESPONSE_VALIDATION_ERROR"
    default_message = "Phản hồi của AI không hợp lệ."
    retryable = False
