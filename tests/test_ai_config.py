"""Unit test cho cấu hình và factory của lớp AI."""

import asyncio

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.ai import AIConfigurationError, GeminiProvider, create_ai_provider


def _settings(**overrides) -> Settings:
    """Tạo Settings hermetic, không đọc file .env cục bộ."""
    values = {
        "database_url": "sqlite+pysqlite:///:memory:",
        "secret_key": "test-ai-config-secret-key-at-least-32-bytes",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_ai_settings_have_safe_defaults():
    settings = _settings()

    assert settings.ai_provider == "gemini"
    assert settings.gemini_api_key.get_secret_value() == ""
    assert settings.gemini_model == ""
    assert settings.ai_timeout == 30.0
    assert settings.ai_max_retries == 2


def test_ai_settings_read_explicit_values():
    settings = _settings(
        ai_provider="GEMINI",
        gemini_api_key="fake-key-for-test",
        gemini_model="  gemini-test-model  ",
        ai_timeout=12.5,
        ai_max_retries=4,
    )

    assert settings.ai_provider == "gemini"
    assert settings.gemini_api_key.get_secret_value() == "fake-key-for-test"
    assert settings.gemini_model == "gemini-test-model"
    assert settings.ai_timeout == 12.5
    assert settings.ai_max_retries == 4


def test_api_key_is_masked_in_settings_repr():
    settings = _settings(gemini_api_key="super-secret-key-value")

    assert "super-secret-key-value" not in repr(settings)
    assert "super-secret-key-value" not in str(settings)


def test_ai_settings_reject_invalid_timeout_and_retry_values():
    with pytest.raises(ValidationError):
        _settings(ai_timeout=0)
    with pytest.raises(ValidationError):
        _settings(ai_max_retries=-1)
    with pytest.raises(ValidationError):
        _settings(ai_provider="   ")


def test_factory_rejects_missing_api_key():
    settings = _settings(gemini_model="gemini-test-model")

    with pytest.raises(AIConfigurationError) as info:
        create_ai_provider(settings)

    assert info.value.code == "AI_CONFIGURATION_ERROR"
    assert "GEMINI_API_KEY" in info.value.message


def test_factory_rejects_missing_model():
    settings = _settings(gemini_api_key="fake-key-for-test")

    with pytest.raises(AIConfigurationError) as info:
        create_ai_provider(settings)

    assert info.value.code == "AI_CONFIGURATION_ERROR"
    assert "GEMINI_MODEL" in info.value.message


def test_factory_rejects_unsupported_provider():
    settings = _settings(
        ai_provider="openai",
        gemini_api_key="fake-key-for-test",
        gemini_model="gemini-test-model",
    )

    with pytest.raises(AIConfigurationError) as info:
        create_ai_provider(settings)

    assert info.value.code == "AI_CONFIGURATION_ERROR"
    assert "openai" in info.value.message


def test_factory_builds_gemini_provider_from_valid_config():
    settings = _settings(
        gemini_api_key="fake-key-for-test",
        gemini_model="gemini-test-model",
        ai_timeout=15,
    )

    provider = create_ai_provider(settings)
    try:
        assert isinstance(provider, GeminiProvider)
        assert provider.name == "gemini"
    finally:
        asyncio.run(provider.aclose())
