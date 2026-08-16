"""Common interface every LLM provider implements, so the gateway and
engine never depend on a specific vendor SDK."""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Raised when a provider cannot produce a completion (auth, network, timeout)."""


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, messages: list[dict]) -> str: ...
