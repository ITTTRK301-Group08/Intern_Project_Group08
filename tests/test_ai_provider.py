"""Unit test cho GeminiProvider, sử dụng client giả thay vì gọi API thật."""

import asyncio

import pytest
from google.genai import errors

from app.services.ai import gemini_provider as gemini_provider_module
from app.services.ai.exceptions import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidRequestError,
    AIProviderError,
    AIRateLimitError,
    AITimeoutError,
)
from app.services.ai.gemini_provider import GeminiProvider

API_KEY = "fake-gemini-key-for-tests"
MODEL = "gemini-test-model"


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
    captured = {}
    response = _FakeGenerateResponse('{"ok": true}')

    class _FakeClient:
        def __init__(self, *, api_key, http_options):
            self.models = _FakeModels(response)
            self.aio = _FakeAio(self.models)
            captured["models"] = self.models

    monkeypatch.setattr(gemini_provider_module.genai, "Client", _FakeClient)
    provider = _provider()

    class _Schema:
        pass

    asyncio.run(
        provider.generate(
            prompt="Trả về JSON",
            response_schema=_Schema,
            system_instruction="Chỉ trả JSON",
        )
    )

    config = captured["models"].calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_schema is _Schema
    assert config.system_instruction == "Chỉ trả JSON"


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
