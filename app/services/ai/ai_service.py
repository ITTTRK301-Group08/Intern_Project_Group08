"""Lớp điều phối AI dùng chung.

`AIService` chịu trách nhiệm:
- Gọi provider theo prompt và schema đầu ra mong muốn.
- Retry có giới hạn chỉ với lỗi tạm thời.
- Bóc Markdown code fence, parse JSON an toàn và xác thực bằng Pydantic v2.
- Không bao giờ trả dữ liệu chưa được xác thực cho tầng nghiệp vụ.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from functools import lru_cache
from typing import Awaitable, Callable, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.services.ai.ai_factory import create_ai_provider
from app.services.ai.base import BaseAIProvider
from app.services.ai.exceptions import (
    AIProviderError,
    AIResponseValidationError,
    AIServiceError,
)

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

# Bắt các khối Markdown code fence, có hoặc không kèm nhãn `json`.
_MARKDOWN_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_MARKDOWN_FENCE_OPEN_PATTERN = re.compile(r"^```[a-zA-Z0-9_-]*\s*", re.IGNORECASE)


class AIService:
    """Điều phối gọi AI, retry, parse JSON và xác thực dữ liệu đầu ra."""

    def __init__(
        self,
        provider: BaseAIProvider,
        *,
        max_retries: int = 2,
        retry_base_delay: float = 0.5,
        retry_max_delay: float = 8.0,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        """Khởi tạo service với provider và chính sách retry.

        `sleep` được phép truyền vào để unit test kiểm tra khoảng nghỉ mà
        không phải chờ thật.
        """
        if max_retries < 0:
            raise ValueError("max_retries không được âm")
        if retry_base_delay < 0 or retry_max_delay < 0:
            raise ValueError("Khoảng nghỉ retry không được âm")

        self._provider = provider
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay
        self._sleep = sleep or asyncio.sleep

    @property
    def provider(self) -> BaseAIProvider:
        """Provider hiện tại mà service đang sử dụng."""
        return self._provider

    @property
    def max_retries(self) -> int:
        """Số lần retry tối đa sau lần gọi đầu tiên."""
        return self._max_retries

    async def generate_text(
        self,
        *,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        """Gọi AI và trả về nội dung thô sau khi áp dụng retry."""
        self._require_prompt(prompt)
        return await self._generate_with_retry(
            prompt=prompt,
            response_schema=None,
            system_instruction=system_instruction,
        )

    async def generate_structured(
        self,
        *,
        prompt: str,
        response_schema: type[SchemaT],
        system_instruction: str | None = None,
    ) -> SchemaT:
        """Gọi AI và trả về instance Pydantic đã được xác thực.

        Nếu phản hồi rỗng, sai cú pháp JSON hoặc không khớp schema, service
        phát sinh `AIResponseValidationError` thay vì trả dữ liệu chưa kiểm tra.
        """
        if not isinstance(response_schema, type) or not issubclass(response_schema, BaseModel):
            raise TypeError("response_schema phải là lớp con của pydantic.BaseModel")

        self._require_prompt(prompt)
        raw_text = await self._generate_with_retry(
            prompt=prompt,
            response_schema=response_schema,
            system_instruction=system_instruction,
        )
        return self._parse_and_validate(raw_text, response_schema)

    async def _generate_with_retry(
        self,
        *,
        prompt: str,
        response_schema: type[BaseModel] | None,
        system_instruction: str | None,
    ) -> str:
        """Gọi provider và retry khi gặp lỗi có thể phục hồi."""
        total_attempts = self._max_retries + 1

        for attempt in range(1, total_attempts + 1):
            try:
                return await self._provider.generate(
                    prompt=prompt,
                    response_schema=response_schema,
                    system_instruction=system_instruction,
                )
            except AIServiceError as exc:
                # Không retry lỗi cấu hình, xác thực, request sai hoặc dữ liệu hỏng.
                if not exc.retryable or attempt >= total_attempts:
                    raise

                delay = self._retry_delay(exc, attempt)
                logger.warning(
                    "Lần gọi AI thứ %d/%d thất bại (%s); thử lại sau %.2f giây.",
                    attempt,
                    total_attempts,
                    exc.code,
                    delay,
                )
                await self._sleep(delay)

        # Không thể tới đây vì vòng lặp luôn return hoặc raise.
        raise AIProviderError("Không thể hoàn tất yêu cầu AI.", provider=self._provider.name)

    def _retry_delay(self, exc: AIServiceError, attempt: int) -> float:
        """Tính khoảng nghỉ trước lần retry kế tiếp.

        Ưu tiên `Retry-After` do nhà cung cấp trả về; nếu không có thì dùng
        exponential backoff và luôn giới hạn bởi `retry_max_delay`.
        """
        if exc.retry_after is not None:
            return min(max(exc.retry_after, 0.0), self._retry_max_delay)

        delay = self._retry_base_delay * (2 ** (attempt - 1))
        return min(delay, self._retry_max_delay)

    @classmethod
    def _parse_and_validate(cls, raw_text: str, response_schema: type[SchemaT]) -> SchemaT:
        """Bóc code fence, parse JSON và xác thực bằng Pydantic."""
        normalized = (raw_text or "").strip()
        if not normalized:
            raise AIResponseValidationError(
                "AI trả về nội dung rỗng, không thể xác thực JSON.",
            )

        candidate = cls._strip_markdown_fence(normalized)
        if not candidate:
            raise AIResponseValidationError(
                "AI trả về nội dung rỗng sau khi bóc Markdown code fence.",
            )

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise AIResponseValidationError(
                "Nội dung AI trả về không phải JSON hợp lệ.",
            ) from exc

        try:
            return response_schema.model_validate(payload)
        except ValidationError as exc:
            raise AIResponseValidationError(
                "Dữ liệu AI trả về không khớp schema yêu cầu.",
            ) from exc

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        """Lấy JSON bên trong Markdown code fence nếu có."""
        match = _MARKDOWN_FENCE_PATTERN.search(text)
        if match:
            return match.group(1).strip()

        # Trường hợp model mở fence nhưng thiếu dấu đóng.
        if text.startswith("```"):
            without_open = _MARKDOWN_FENCE_OPEN_PATTERN.sub("", text, count=1)
            return without_open.replace("```", "").strip()

        return text

    @staticmethod
    def _require_prompt(prompt: str) -> None:
        """Bảo đảm prompt không rỗng trước khi gọi nhà cung cấp AI."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt không được rỗng")


def create_ai_service(settings: Settings | None = None) -> AIService:
    """Tạo `AIService` từ cấu hình hiện tại của ứng dụng."""
    configured = settings or get_settings()
    return AIService(
        provider=create_ai_provider(configured),
        max_retries=configured.ai_max_retries,
    )


@lru_cache
def get_ai_service() -> AIService:
    """Trả về `AIService` dùng chung cho toàn bộ backend.

    Provider chỉ được khởi tạo ở lần gọi đầu tiên, nhờ đó ứng dụng vẫn khởi
    động được khi chưa cấu hình API Key.
    """
    return create_ai_service()
