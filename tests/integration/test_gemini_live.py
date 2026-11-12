import asyncio
import os

import pytest

from app.core.config import Settings
from app.services.ai import GeminiProvider


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_GEMINI_LIVE_TESTS") != "1",
    reason="set RUN_GEMINI_LIVE_TESTS=1 to call the live Gemini API",
)


def test_gemini_returns_a_live_response():
    settings = Settings()
    api_key = settings.gemini_api_key.get_secret_value()
    if not api_key or not settings.gemini_model:
        pytest.fail(
            "Configure GEMINI_API_KEY and GEMINI_MODEL before opting into live tests"
        )

    provider = GeminiProvider(
        api_key=api_key,
        model=settings.gemini_model,
        timeout=settings.ai_timeout,
    )

    async def generate_response() -> str:
        try:
            return await provider.generate(
                prompt="Reply with the single word: READY"
            )
        finally:
            await provider.aclose()

    response = asyncio.run(generate_response())
    assert response.strip()
    assert "READY" in response.upper()