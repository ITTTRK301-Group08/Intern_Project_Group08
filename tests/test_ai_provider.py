"""Unit test cho GeminiProvider, sử dụng client giả thay vì gọi API thật."""

import asyncio
import json

import pytest
from google.genai import errors
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.ai import gemini_provider as gemini_provider_module
from app.services.ai.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from app.services.ai.gemini_provider import (
    GeminiProvider,
    _to_gemini_compatible_schema,
)

API_KEY = "fake-gemini-key-for-tests"
MODEL = "gemini-test-model"


class _NestedCriterion(BaseModel):
    """Schema lồng nhau có cả hai khóa không được gửi Gemini."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"additional_properties": False},
    )

    score: int = Field(ge=1, le=5)


class _NestedQuestion(BaseModel):
    """Schema câu hỏi dùng để kiểm tra map schema con."""

    model_config = ConfigDict(extra="forbid")

    question_text: str = Field(min_length=1, max_length=2000)
    evaluation_criteria: list[_NestedCriterion] = Field(min_length=1, max_length=10)


class _NestedResponse(BaseModel):
    """Schema gốc mô phỏng cấu trúc response có nhiều cấp."""

    model_config = ConfigDict(extra="forbid")

    questions: list[_NestedQuestion] = Field(min_length=3, max_length=3)


def _find_key(node, key):
    """Trả về các vị trí chứa khóa cần kiểm tra trong JSON Schema."""
    found = []
    if isinstance(node, dict):
        if key in node:
            found.append(node)
        for value in node.values():
            found.extend(_find_key(value, key))
    elif isinstance(node, list):
        for item in node:
            found.extend(_find_key(item, key))
    return found


def _valid_nested_payload():
    """Tạo payload hợp lệ tối thiểu cho các test validation."""
    return {
        "questions": [
            {
                "question_text": f"Câu hỏi {index}",
                "evaluation_criteria": [{"score": 3}],
            }
            for index in range(1, 4)
        ]
    }


class _FakeGenerateResponse:
    """Phản hồi tối giản mô phỏng GenerateContentResponse."""

    def __init__(self, text):
        self.text = text


class _FakeHeadersResponse:
    """Phản hồi HTTP tối giản chỉ chứa header cần kiểm tra."""

    def __init__(self, headers):
        self.headers = headers


class _FakeModels:
    """Mô phỏng aio.models.generate_content."""

    def __init__(self, outcome):
        self._outcome = outcome
        self.calls = []

    async def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome


class _FakeAio:
    """Mô phỏng client.aio."""

    def __init__(self, models):
        self.models = models
        self.closed = False

    async def aclose(self):
        self.closed = True


def _install_fake_client(monkeypatch, outcome):
    """Gắn client giả vào module provider và trả về dữ liệu đã ghi nhận."""
    captured = {}

    class _FakeClient:
        def __init__(self, *, api_key, http_options):
            captured["api_key"] = api_key
            captured["http_options"] = http_options
            self.models = _FakeModels(outcome)
            self.aio = _FakeAio(self.models)
            captured["models"] = self.models

    monkeypatch.setattr(gemini_provider_module.genai, "Client", _FakeClient)
    return captured


def _provider(timeout=12.5):
    return GeminiProvider(api_key=API_KEY, model=MODEL, timeout=timeout)


def test_provider_requires_api_key():
    with pytest.raises(AIConfigurationError) as info:
        GeminiProvider(api_key="  ", model=MODEL)

    assert "GEMINI_API_KEY" in info.value.message


def test_provider_requires_model():
    with pytest.raises(AIConfigurationError) as info:
        GeminiProvider(api_key=API_KEY, model="   ")

    assert "GEMINI_MODEL" in info.value.message


def test_provider_configures_timeout_in_milliseconds_and_disables_sdk_retry(monkeypatch):
    captured = _install_fake_client(monkeypatch, _FakeGenerateResponse("ok"))

    _provider(timeout=12.5)

    http_options = captured["http_options"]
    assert http_options.timeout == 12500
    assert http_options.retry_options.attempts == 1
    assert captured["api_key"] == API_KEY


def test_provider_returns_generated_text(monkeypatch):
    captured = _install_fake_client(monkeypatch, _FakeGenerateResponse("nội dung AI"))
    provider = _provider()

    result = asyncio.run(provider.generate(prompt="Xin chào"))

    assert result == "nội dung AI"
    assert captured["models"].calls[0]["model"] == MODEL
    assert captured["models"].calls[0]["contents"] == "Xin chào"
    assert provider.name == "gemini"


def test_provider_sends_schema_and_system_instruction(monkeypatch):
    captured = _install_fake_client(monkeypatch, _FakeGenerateResponse('{"ok": true}'))
    provider = _provider()

    asyncio.run(
        provider.generate(
            prompt="Trả về JSON",
            response_schema=_NestedResponse,
            system_instruction="Chỉ trả JSON",
        )
    )

    config = captured["models"].calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert isinstance(config.response_schema, dict)
    assert config.response_schema == _to_gemini_compatible_schema(_NestedResponse)
    assert _find_key(config.response_schema, "additionalProperties") == []
    assert _find_key(config.response_schema, "additional_properties") == []
    assert config.system_instruction == "Chỉ trả JSON"


def test_schema_conversion_is_json_serializable():
    """Schema sau chuyển đổi phải gửi được qua SDK dưới dạng JSON thuần."""
    converted = _to_gemini_compatible_schema(_NestedResponse)
    serialized = json.dumps(converted)

    assert "additionalProperties" not in serialized
    assert "additional_properties" not in serialized


def test_schema_conversion_removes_unsupported_keys_at_every_level():
    original = _NestedResponse.model_json_schema()
    converted = _to_gemini_compatible_schema(_NestedResponse)

    # Schema gốc của Pydantic vẫn còn các khóa bị loại bỏ (không bị sửa tại chỗ).
    assert _find_key(original, "additionalProperties")
    assert _find_key(original, "additional_properties")

    # Schema gửi Gemini không còn khóa nào ở bất kỳ cấp nào.
    assert _find_key(converted, "additionalProperties") == []
    assert _find_key(converted, "additional_properties") == []


def test_schema_conversion_keeps_supported_constraints():
    converted = _to_gemini_compatible_schema(_NestedResponse)

    assert converted["type"] == "object"
    assert "properties" in converted
    assert converted["required"] == ["questions"]

    questions_schema = converted["properties"]["questions"]
    assert questions_schema["type"] == "array"
    assert questions_schema["items"]["$ref"] == "#/$defs/_NestedQuestion"

    question_schema = converted["$defs"]["_NestedQuestion"]
    assert question_schema["type"] == "object"
    assert "properties" in question_schema
    assert set(question_schema["required"]) == {"question_text", "evaluation_criteria"}
    assert question_schema["properties"]["question_text"]["type"] == "string"

    criteria_schema = question_schema["properties"]["evaluation_criteria"]
    assert criteria_schema["type"] == "array"
    assert criteria_schema["items"]["$ref"] == "#/$defs/_NestedCriterion"
    assert question_schema["properties"]["evaluation_criteria"]["type"] == "array"


def test_schema_conversion_drops_bounds_rejected_by_gemini():
    """Gemini trả 400 khi payload có ràng buộc số lượng/độ dài.

    Các khóa này phải bị lược khỏi payload gửi đi nhưng Pydantic vẫn giữ
    nguyên ràng buộc để xác thực response.
    """
    converted = _to_gemini_compatible_schema(_NestedResponse)
    serialized = json.dumps(converted)

    for key in (
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "minProperties",
        "maxProperties",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
    ):
        assert key not in serialized

    # Ràng buộc vẫn tồn tại trong JSON Schema gốc của Pydantic.
    original = _NestedResponse.model_json_schema()
    assert _find_key(original, "minItems")
    assert _find_key(original, "maxLength")
    assert _find_key(original, "minimum")


def test_schema_conversion_output_is_accepted_by_gemini_sdk():
    """Payload sau chuyển đổi phải qua được bước validate của SDK Gemini.

    Test này không gọi mạng; nó tái hiện đúng bước ``process_schema`` +
    ``types.Schema.model_validate`` mà SDK chạy trước khi gửi request.
    """
    from google.genai._transformers import process_schema
    from google.genai import types

    for model in (_NestedResponse,):
        converted = _to_gemini_compatible_schema(model)
        candidate = json.loads(json.dumps(converted))
        process_schema(candidate, None)
        validated = types.Schema.model_validate(candidate)
        assert validated is not None


def test_pydantic_still_enforces_bounds_after_conversion():
    """Việc lược khóa khỏi payload không được nới lỏng validation của Pydantic."""
    payload = _valid_nested_payload()
    payload["questions"] = payload["questions"][:2]

    with pytest.raises(ValidationError):
        _NestedResponse.model_validate(payload)

    payload = _valid_nested_payload()
    payload["questions"][0]["question_text"] = ""

    with pytest.raises(ValidationError):
        _NestedResponse.model_validate(payload)


def test_schema_conversion_does_not_mutate_source_schema():
    before = _NestedResponse.model_json_schema()
    _to_gemini_compatible_schema(_NestedResponse)
    after = _NestedResponse.model_json_schema()

    assert after == before
    assert _find_key(before, "additionalProperties")
    assert _find_key(after, "additionalProperties")


def test_pydantic_still_rejects_unknown_root_field():
    payload = _valid_nested_payload()
    payload["unexpected"] = True

    with pytest.raises(ValidationError) as info:
        _NestedResponse.model_validate(payload)

    assert "unexpected" in str(info.value)


def test_pydantic_still_rejects_unknown_nested_field():
    payload = _valid_nested_payload()
    payload["questions"][0]["unexpected"] = True

    with pytest.raises(ValidationError) as info:
        _NestedResponse.model_validate(payload)

    assert "unexpected" in str(info.value)


def test_pydantic_still_rejects_unknown_criterion_field():
    payload = _valid_nested_payload()
    payload["questions"][0]["evaluation_criteria"][0]["unexpected"] = True

    with pytest.raises(ValidationError) as info:
        _NestedResponse.model_validate(payload)

    assert "unexpected" in str(info.value)


def test_provider_returns_empty_string_when_response_has_no_text(monkeypatch):
    _install_fake_client(monkeypatch, _FakeGenerateResponse(None))
    provider = _provider()

    assert asyncio.run(provider.generate(prompt="Xin chào")) == ""


def test_provider_maps_authentication_error(monkeypatch):
    error = errors.APIError(
        401,
        {"error": {"code": 401, "status": "UNAUTHENTICATED", "message": "invalid key"}},
    )
    _install_fake_client(monkeypatch, error)
    provider = _provider()

    with pytest.raises(AIAuthenticationError) as info:
        asyncio.run(provider.generate(prompt="Xin chào"))

    assert info.value.retryable is False
    assert API_KEY not in str(info.value)


def test_provider_maps_forbidden_as_authentication_error(monkeypatch):
    error = errors.APIError(
        403,
        {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "denied"}},
    )
    _install_fake_client(monkeypatch, error)
    provider = _provider()

    with pytest.raises(AIAuthenticationError) as info:
        asyncio.run(provider.generate(prompt="Xin chào"))

    assert info.value.retryable is False
    assert API_KEY not in str(info.value)


def test_provider_maps_rate_limit_error_with_retry_after(monkeypatch):
    error = errors.APIError(
        429,
        {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}},
        _FakeHeadersResponse({"Retry-After": "7"}),
    )
    _install_fake_client(monkeypatch, error)
    provider = _provider()

    with pytest.raises(AIRateLimitError) as info:
        asyncio.run(provider.generate(prompt="Xin chào"))

    assert info.value.retryable is True
    assert info.value.retry_after == 7.0


def test_provider_maps_server_error_as_retryable(monkeypatch):
    error = errors.APIError(
        503,
        {"error": {"code": 503, "status": "UNAVAILABLE", "message": "overloaded"}},
    )
    _install_fake_client(monkeypatch, error)
    provider = _provider()

    with pytest.raises(AIProviderError) as info:
        asyncio.run(provider.generate(prompt="Xin chào"))

    assert info.value.retryable is True


def test_provider_maps_gateway_timeout_as_timeout_error(monkeypatch):
    error = errors.APIError(
        504,
        {"error": {"code": 504, "status": "DEADLINE_EXCEEDED", "message": "timeout"}},
    )
    _install_fake_client(monkeypatch, error)
    provider = _provider()

    with pytest.raises(AITimeoutError) as info:
        asyncio.run(provider.generate(prompt="Xin chào"))

    assert info.value.retryable is True


def test_provider_maps_invalid_request_as_non_retryable(monkeypatch):
    error = errors.APIError(
        400,
        {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "bad request"}},
    )
    _install_fake_client(monkeypatch, error)
    provider = _provider()

    with pytest.raises(AIInvalidRequestError) as info:
        asyncio.run(provider.generate(prompt="Xin chào"))

    assert info.value.retryable is False


def test_provider_maps_network_error_as_retryable(monkeypatch):
    _install_fake_client(monkeypatch, ConnectionError("mất kết nối"))
    provider = _provider()

    with pytest.raises(AIProviderError) as info:
        asyncio.run(provider.generate(prompt="Xin chào"))

    assert info.value.retryable is True


def test_provider_maps_timeout_error(monkeypatch):
    _install_fake_client(monkeypatch, asyncio.TimeoutError())
    provider = _provider()

    with pytest.raises(AITimeoutError) as info:
        asyncio.run(provider.generate(prompt="Xin chào"))

    assert info.value.retryable is True


def test_provider_closes_async_client(monkeypatch):
    captured = {}

    class _FakeClient:
        def __init__(self, *, api_key, http_options):
            self.models = _FakeModels(_FakeGenerateResponse("ok"))
            self.aio = _FakeAio(self.models)
            captured["client"] = self

    monkeypatch.setattr(gemini_provider_module.genai, "Client", _FakeClient)
    provider = _provider()

    asyncio.run(provider.aclose())

    assert captured["client"].aio.closed is True
