"""Triển khai nhà cung cấp AI sử dụng Google Gemini (SDK `google-genai`).

Provider chỉ thực hiện một lần gọi SDK cho mỗi yêu cầu. Cơ chế retry được đặt
tập trung ở `AIService` để tránh nhân số request ngoài ý muốn.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.services.ai.base import BaseAIProvider
from app.services.ai.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AIServiceError,
    AITimeoutError,
)

logger = logging.getLogger(__name__)

# Các mã HTTP được xem là lỗi hết thời gian chờ từ phía máy chủ.
_TIMEOUT_STATUS_CODES = frozenset({408, 504})
# Các mã HTTP thể hiện lỗi xác thực hoặc phân quyền.
_AUTHENTICATION_STATUS_CODES = frozenset({401, 403})


class GeminiProvider(BaseAIProvider):
    """Quản lý việc gửi yêu cầu và nhận phản hồi từ Gemini."""

    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float = 30.0,
    ) -> None:
        """Khởi tạo client Gemini từ cấu hình đã được xác thực.

        API Key và tên model đều phải có giá trị. Client được tạo ngay tại đây
        nhưng chưa phát sinh kết nối mạng; lỗi cấu hình sẽ được báo rõ ràng
        thay vì để SDK thất bại một cách khó hiểu về sau.
        """
        normalized_key = (api_key or "").strip()
        normalized_model = (model or "").strip()

        if not normalized_key:
            raise AIConfigurationError(
                "Thiếu GEMINI_API_KEY: hãy cấu hình API Key trước khi sử dụng AI.",
                provider=self.name,
            )
        if not normalized_model:
            raise AIConfigurationError(
                "Thiếu GEMINI_MODEL: hãy cấu hình model Gemini cần sử dụng.",
                provider=self.name,
            )

        self._model = normalized_model
        # `HttpOptions.timeout` của SDK tính bằng mili-giây.
        timeout_ms = max(1, int(round(float(timeout) * 1000)))
        http_options = types.HttpOptions(
            timeout=timeout_ms,
            # Tắt retry nội bộ của SDK; `AIService` là tầng duy nhất được retry.
            retry_options=types.HttpRetryOptions(attempts=1),
        )
        try:
            self._client = genai.Client(api_key=normalized_key, http_options=http_options)
        except Exception as exc:  # pragma: no cover - phụ thuộc SDK, giữ an toàn
            logger.debug("Không khởi tạo được client Gemini: %s", type(exc).__name__)
            # Không chain exception gốc để tránh vô tình đưa API Key vào traceback.
            raise AIConfigurationError(
                "Không thể khởi tạo client Gemini từ cấu hình hiện tại.",
                provider=self.name,
            ) from None

    async def generate(
        self,
        *,
        prompt: str,
        response_schema: type[BaseModel] | None = None,
        system_instruction: str | None = None,
    ) -> str:
        """Gửi prompt tới Gemini và trả về nội dung thô.

        Nếu có `response_schema`, yêu cầu Gemini trả về JSON theo đúng schema.
        Kết quả vẫn được `AIService` xác thực lại, không mặc định tin tưởng.
        """
        config = types.GenerateContentConfig()
        if response_schema is not None:
            config.response_mime_type = "application/json"
            config.response_schema = response_schema
        if system_instruction:
            config.system_instruction = system_instruction

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
        except errors.APIError as exc:
            raise self._map_api_error(exc) from exc
        except (asyncio.TimeoutError, TimeoutError) as exc:
            raise AITimeoutError(
                "Yêu cầu tới Gemini đã hết thời gian chờ.",
                provider=self.name,
            ) from exc
        except Exception as exc:
            # Không chain exception gốc để tránh đưa thông tin nội bộ vào traceback.
            raise self._map_unexpected_error(exc) from None

        return self._extract_text(response)

    async def aclose(self) -> None:
        """Đóng client bất đồng bộ để giải phóng tài nguyên mạng."""
        with contextlib.suppress(Exception):
            await self._client.aio.aclose()

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Lấy nội dung văn bản từ phản hồi SDK một cách an toàn."""
        try:
            text = response.text
        except Exception:  # pragma: no cover - phòng khi SDK đổi hành vi
            text = None
        return text or ""

    def _map_api_error(self, exc: errors.APIError) -> AIServiceError:
        """Chuyển lỗi HTTP của SDK thành exception chuẩn hóa.

        Chỉ sử dụng mã trạng thái và thông điệp do mình kiểm soát; không đưa
        nội dung chi tiết của SDK vào exception để tránh lộ thông tin nội bộ.
        """
        status = self._status_code(exc)
        retry_after = self._retry_after_seconds(exc)

        if status == 429:
            return AIRateLimitError(
                "Gemini đã giới hạn số lượng yêu cầu.",
                provider=self.name,
                retry_after=retry_after,
            )
        if status in _AUTHENTICATION_STATUS_CODES:
            return AIAuthenticationError(
                "Gemini từ chối xác thực API Key hoặc quyền truy cập.",
                provider=self.name,
            )
        if status in _TIMEOUT_STATUS_CODES:
            return AITimeoutError(
                "Gemini phản hồi quá thời gian chờ.",
                provider=self.name,
            )
        if 400 <= status < 500:
            return AIInvalidRequestError(
                "Yêu cầu gửi tới Gemini không hợp lệ.",
                provider=self.name,
            )
        return AIProviderError(
            "Gemini đang gặp lỗi tạm thời, vui lòng thử lại.",
            provider=self.name,
        )

    def _map_unexpected_error(self, exc: Exception) -> AIServiceError:
        """Chuyển lỗi mạng hoặc lỗi không xác định thành exception chuẩn hóa."""
        error_name = type(exc).__name__
        if "timeout" in error_name.casefold():
            return AITimeoutError(
                "Yêu cầu tới Gemini đã hết thời gian chờ.",
                provider=self.name,
            )
        logger.debug("Lỗi không xác định từ Gemini: %s", error_name)
        return AIProviderError(
            "Không thể kết nối tới Gemini, vui lòng thử lại.",
            provider=self.name,
        )

    @staticmethod
    def _status_code(exc: errors.APIError) -> int:
        """Đọc mã HTTP từ APIError, trả về 0 nếu không xác định được."""
        try:
            return int(getattr(exc, "code", 0) or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _retry_after_seconds(exc: errors.APIError) -> float | None:
        """Đọc header Retry-After (dạng số giây) nếu SDK cung cấp."""
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", None)
        if headers is None:
            return None
        try:
            raw_value = headers.get("Retry-After") or headers.get("retry-after")
        except Exception:  # pragma: no cover - header có thể không hỗ trợ get
            return None
        if raw_value is None:
            return None
        try:
            seconds = float(raw_value)
        except (TypeError, ValueError):
            return None
        return seconds if seconds >= 0 else None
