"""LLMGateway: retry then fallback to the mock provider on completion
failure; classification failure is raised for the caller to handle.

Covers plan test-matrix row: Primary LLM Outage.
"""

import pytest

from src.config.tech_config import Settings
from src.llm.base_provider import ProviderError
from src.llm.gateway import LLMGateway
from src.llm.providers import OpenAIProvider


@pytest.fixture
def gateway():
    return LLMGateway(Settings(openai_api_key="test-key"))


async def test_complete_falls_back_to_mock_when_primary_exhausts_retries(gateway, monkeypatch):
    async def always_fails(self, messages):
        raise ProviderError("simulated outage")

    monkeypatch.setattr(OpenAIProvider, "generate", always_fails)

    result = await gateway.complete([{"role": "user", "content": "hi"}])

    assert result.provider == "mock"


async def test_complete_uses_primary_when_healthy(gateway, monkeypatch):
    async def always_succeeds(self, messages):
        return "a real answer"

    monkeypatch.setattr(OpenAIProvider, "generate", always_succeeds)

    result = await gateway.complete([{"role": "user", "content": "hi"}])

    assert result.provider == "openai"
    assert result.text == "a real answer"


async def test_classify_raises_after_exhausting_retries(gateway, monkeypatch):
    async def always_fails(self, messages):
        raise ProviderError("simulated outage")

    monkeypatch.setattr(OpenAIProvider, "generate", always_fails)

    with pytest.raises(ProviderError):
        await gateway.classify([{"role": "user", "content": "hi"}])


async def test_missing_api_key_falls_back_to_mock():
    gateway = LLMGateway(Settings(openai_api_key=None))

    result = await gateway.complete([{"role": "user", "content": "hi"}])

    assert result.provider == "mock"
