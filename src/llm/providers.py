"""Concrete LLM providers: OpenAI (real) and Mock (deterministic, offline)."""

import asyncio

from openai import AsyncOpenAI, OpenAIError

from src.llm.base_provider import BaseLLMProvider, ProviderError


class ProviderConfig:
    def __init__(self, model: str, temperature: float, max_tokens: int):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens


class OpenAIProvider(BaseLLMProvider):
    """Wraps the OpenAI chat completions API. The client is built lazily on
    first use so a missing API key surfaces as a ProviderError - triggering
    gateway fallback - instead of crashing app startup."""

    def __init__(self, name: str, api_key: str | None, config: ProviderConfig, timeout_seconds: float):
        self.name = name
        self._api_key = api_key
        self._config = config
        self._timeout_seconds = timeout_seconds
        self._client: AsyncOpenAI | None = None

    async def generate(self, messages: list[dict]) -> str:
        if not self._api_key:
            raise ProviderError(f"{self.name}: OPENAI_API_KEY is not configured")
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key, timeout=self._timeout_seconds)

        try:
            response = await self._client.chat.completions.create(
                model=self._config.model,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                messages=messages,
            )
        except OpenAIError as exc:
            raise ProviderError(f"{self.name}: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise ProviderError(f"{self.name}: empty completion")
        return content.strip()


class MockLLMProvider(BaseLLMProvider):
    """Deterministic offline provider - keeps the assignment runnable without
    any API key and gives the gateway a fallback that cannot itself fail."""

    name = "mock"

    async def generate(self, messages: list[dict]) -> str:
        await asyncio.sleep(0)  # stay genuinely async so callers can await it uniformly
        question = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return (
            "[mock response] This is a placeholder reading generated without a "
            f"live LLM provider, based on the context supplied for: {question[:200]}"
        )
