"""Unit test cho AIService: JSON, Pydantic, timeout và retry."""

import asyncio

import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.schemas.ai import AIStructuredResponse
from app.services.ai import (
    AIAuthenticationError,
    AIProviderError,
    AIRateLimitError,
    AIService,
    AIResponseValidationError,
    BaseAIProvider,
    create_ai_service,
)

VALID_JSON = '{"title": "Lộ trình Python", "items": [{"label": "Python", "score": 8}]}'


class NestedItem(BaseModel):
    label: str
    score: int


class SampleSchema(AIStructuredResponse):
    title: str
    items: list[NestedItem]


class FakeProvider(BaseAIProvider):
    """Provider giả trả về lần lượt các kết quả hoặc exception đã định trước."""

    name = "fake"

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = 0
        self.last_response_schema = None
        self.last_system_instruction = None

    async def generate(self, *, prompt, response_schema=None, system_instruction=None):
        self.calls += 1
        self.last_response_schema = response_schema
        self.last_system_instruction = system_instruction
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _service(provider, **kwargs):
    """Tạo AIService với sleep giả để kiểm tra khoảng nghỉ retry."""
    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    service = AIService(provider, sleep=record_sleep, **kwargs)
    return service, delays


def _structured(service):
    return asyncio.run(
        service.generate_structured(prompt="Tạo lộ trình", response_schema=SampleSchema)
    )


def test_generate_structured_returns_validated_model():
    provider = FakeProvider([VALID_JSON])
    service, delays = _service(provider)

    result = _structured(service)

    assert isinstance(result, SampleSchema)
    assert result.title == "Lộ trình Python"
    assert result.items[0].label == "Python"
    assert result.items[0].score == 8
    assert provider.calls == 1
    assert provider.last_response_schema is SampleSchema
    assert delays == []


def test_generate_structured_accepts_markdown_fence():
    provider = FakeProvider([f"```json\n{VALID_JSON}\n```"])
    service, _ = _service(provider)

    result = _structured(service)

    assert result.title == "Lộ trình Python"


def test_generate_structured_accepts_fence_without_language_and_surrounding_text():
    provider = FakeProvider([f"Đây là kết quả:\n```\n{VALID_JSON}\n```\nHết."])
    service, _ = _service(provider)

    result = _structured(service)

    assert result.items[0].score == 8


def test_generate_structured_rejects_empty_response():
    provider = FakeProvider(["   "])
    service, _ = _service(provider)

    with pytest.raises(AIResponseValidationError) as info:
        _structured(service)

    assert info.value.code == "AI_RESPONSE_VALIDATION_ERROR"
    assert provider.calls == 1


def test_generate_structured_rejects_invalid_json():
    provider = FakeProvider(["{title: khong-hop-le}"])
    service, _ = _service(provider)

    with pytest.raises(AIResponseValidationError):
        _structured(service)


def test_generate_structured_rejects_missing_required_field():
    provider = FakeProvider(['{"title": "Thiếu items"}'])
    service, _ = _service(provider)

    with pytest.raises(AIResponseValidationError):
        _structured(service)


def test_generate_structured_rejects_wrong_field_type():
    provider = FakeProvider(['{"title": "Sai kiểu", "items": [{"label": "Python", "score": "cao"}]}'])
    service, _ = _service(provider)

    with pytest.raises(AIResponseValidationError):
        _structured(service)


def test_generate_structured_rejects_invalid_nested_data():
    provider = FakeProvider(['{"title": "Thiếu label", "items": [{"score": 8}]}'])
    service, _ = _service(provider)

    with pytest.raises(AIResponseValidationError):
        _structured(service)


def test_generate_structured_rejects_unexpected_fields():
    provider = FakeProvider(
        ['{"title": "Thừa trường", "items": [], "unexpected": "giá trị"}']
    )
    service, _ = _service(provider)

    with pytest.raises(AIResponseValidationError):
        _structured(service)


def test_validation_error_is_not_retried():
    provider = FakeProvider(["{khong-hop-le}", VALID_JSON])
    service, delays = _service(provider, max_retries=2)

    with pytest.raises(AIResponseValidationError):
        _structured(service)

    assert provider.calls == 1
    assert delays == []


def test_retry_transient_error_then_succeeds():
    provider = FakeProvider([AIProviderError("tạm thời", provider="fake"), VALID_JSON])
    service, delays = _service(provider, max_retries=2, retry_base_delay=0.5)

    result = _structured(service)

    assert isinstance(result, SampleSchema)
    assert provider.calls == 2
    assert delays == [0.5]


def test_retry_exhaustion_raises_provider_error():
    provider = FakeProvider(
        [
            AIProviderError("lỗi 1", provider="fake"),
            AIProviderError("lỗi 2", provider="fake"),
            AIProviderError("lỗi 3", provider="fake"),
        ]
    )
    service, delays = _service(provider, max_retries=2, retry_base_delay=0.5)

    with pytest.raises(AIProviderError):
        _structured(service)

    assert provider.calls == 3
    assert delays == [0.5, 1.0]


def test_non_retryable_error_is_not_retried():
    provider = FakeProvider([AIAuthenticationError("sai key", provider="fake")])
    service, delays = _service(provider, max_retries=2)

    with pytest.raises(AIAuthenticationError):
        _structured(service)

    assert provider.calls == 1
    assert delays == []


def test_retry_honors_retry_after_header():
    provider = FakeProvider(
        [AIRateLimitError("quota", provider="fake", retry_after=3.5), VALID_JSON]
    )
    service, delays = _service(provider, max_retries=2, retry_max_delay=8.0)

    _structured(service)

    assert provider.calls == 2
    assert delays == [3.5]


def test_retry_delay_is_capped():
    provider = FakeProvider(
        [AIRateLimitError("quota", provider="fake", retry_after=999.0), VALID_JSON]
    )
    service, delays = _service(provider, max_retries=2, retry_max_delay=8.0)

    _structured(service)

    assert delays == [8.0]


def test_zero_retries_means_single_attempt():
    provider = FakeProvider([AIProviderError("tạm thời", provider="fake")])
    service, delays = _service(provider, max_retries=0)

    with pytest.raises(AIProviderError):
        _structured(service)

    assert provider.calls == 1
    assert delays == []


def test_generate_text_returns_raw_content():
    provider = FakeProvider(["nội dung thô"])
    service, _ = _service(provider)

    result = asyncio.run(
        service.generate_text(prompt="Xin chào", system_instruction="Ngắn gọn")
    )

    assert result == "nội dung thô"
    assert provider.last_response_schema is None
    assert provider.last_system_instruction == "Ngắn gọn"


def test_empty_prompt_is_rejected_before_provider_call():
    provider = FakeProvider([VALID_JSON])
    service, _ = _service(provider)

    with pytest.raises(ValueError):
        asyncio.run(
            service.generate_structured(prompt="  ", response_schema=SampleSchema)
        )

    assert provider.calls == 0


def test_response_schema_must_be_pydantic_model():
    provider = FakeProvider([VALID_JSON])
    service, _ = _service(provider)

    with pytest.raises(TypeError):
        asyncio.run(
            service.generate_structured(prompt="Tạo lộ trình", response_schema=dict)
        )

    assert provider.calls == 0


def test_service_rejects_negative_retry_settings():
    provider = FakeProvider([])

    with pytest.raises(ValueError):
        AIService(provider, max_retries=-1)
    with pytest.raises(ValueError):
        AIService(provider, retry_base_delay=-1)
    with pytest.raises(ValueError):
        AIService(provider, retry_max_delay=-1)


def test_create_ai_service_uses_configured_max_retries():
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        secret_key="test-ai-service-secret-key-at-least-32-bytes",
        gemini_api_key="fake-key-for-test",
        gemini_model="gemini-test-model",
        ai_max_retries=3,
        _env_file=None,
    )

    service = create_ai_service(settings)
    try:
        assert service.max_retries == 3
        assert service.provider.name == "gemini"
    finally:
        asyncio.run(service.provider.aclose())
