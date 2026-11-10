"""Hợp đồng chung cho mọi nhà cung cấp AI."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class BaseAIProvider(ABC):
    """Giao diện chung để tầng nghiệp vụ không phụ thuộc SDK cụ thể.

    Provider chỉ chịu trách nhiệm giao tiếp với nhà cung cấp và trả về nội dung
    thô. Việc parse JSON, retry và xác thực Pydantic do `AIService` đảm nhiệm.
    """

    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        response_schema: type[BaseModel] | None = None,
        system_instruction: str | None = None,
    ) -> str:
        """Gửi prompt và trả về nội dung thô do nhà cung cấp sinh ra.

        `response_schema` là gợi ý để provider yêu cầu structured output;
        kết quả vẫn phải được `AIService` xác thực lại bằng Pydantic.
        """

    async def aclose(self) -> None:
        """Giải phóng tài nguyên của provider nếu có.

        Mặc định provider không giữ tài nguyên nên không cần làm gì.
        """
        return None
