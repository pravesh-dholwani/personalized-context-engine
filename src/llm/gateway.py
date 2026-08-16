"""Resilient, provider-agnostic LLM gateway.

Wraps retry + fallback plumbing so callers (the analyzer and the engine)
only ever ask "classify this" or "complete this" - never touching a vendor
SDK or a specific failure mode.

Classification and completion fail differently on purpose: a classification
failure is handled by the caller falling back to keyword rules, while a
completion failure falls back to the mock provider here in the gateway,
per llm_config.yaml's resilience settings.
"""

import asyncio
import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from src.config.tech_config import Settings
from src.llm.base_provider import BaseLLMProvider, ProviderError
from src.llm.providers import MockLLMProvider, OpenAIProvider, ProviderConfig
from src.models.internal_models import ProviderResult

logger = logging.getLogger(__name__)

_DEFAULT_COMPLETION_TIMEOUT_SECONDS = 10.0


class _ProviderSpec(BaseModel):
    model: str
    temperature: float
    maxTokens: int | None = None


class _IntentClassifierResilience(BaseModel):
    primaryProvider: str
    fallbackStrategy: str
    maxRetries: int
    timeoutSeconds: float


class _CompletionResilience(BaseModel):
    primaryProvider: str
    fallbackProviders: list[str]
    finalFallbackProvider: str
    maxRetries: int
    backoffBaseMs: int


@lru_cache
def _load_llm_config(path: str = "config/llm_config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text())


class LLMGateway:
    def __init__(self, settings: Settings, config_path: str = "config/llm_config.yaml"):
        raw = _load_llm_config(config_path)
        specs = {name: _ProviderSpec(**spec) for name, spec in raw["llmProviders"].items()}
        classifier_cfg = _IntentClassifierResilience(**raw["resilience"]["intentClassifier"])
        completion_cfg = _CompletionResilience(**raw["resilience"]["completion"])

        self._classifier_max_retries = classifier_cfg.maxRetries
        self._completion_max_retries = completion_cfg.maxRetries
        self._completion_backoff_base_ms = completion_cfg.backoffBaseMs

        self._classifier_provider = self._build_provider(
            classifier_cfg.primaryProvider, specs, settings, classifier_cfg.timeoutSeconds
        )
        self._primary_completion_provider = self._build_provider(
            completion_cfg.primaryProvider, specs, settings, _DEFAULT_COMPLETION_TIMEOUT_SECONDS
        )
        self._fallback_completion_providers = [
            self._build_provider(name, specs, settings, _DEFAULT_COMPLETION_TIMEOUT_SECONDS)
            for name in completion_cfg.fallbackProviders
        ]
        self._mock_provider = MockLLMProvider()

    @staticmethod
    def _build_provider(
        name: str, specs: dict[str, _ProviderSpec], settings: Settings, timeout_seconds: float
    ) -> OpenAIProvider:
        spec = specs[name]
        return OpenAIProvider(
            name=name,
            api_key=settings.openai_api_key,
            config=ProviderConfig(model=spec.model, temperature=spec.temperature, max_tokens=spec.maxTokens),
            timeout_seconds=timeout_seconds,
        )

    async def classify(self, messages: list[dict]) -> str:
        """Raises ProviderError if the LLM classifier is unavailable - the
        caller is expected to fall back to keyword matching, not to mock."""
        return await self._call_with_retries(
            self._classifier_provider, messages, self._classifier_max_retries, backoff_base_ms=0
        )

    async def complete(self, messages: list[dict]) -> ProviderResult:
        for provider in [self._primary_completion_provider, *self._fallback_completion_providers]:
            try:
                text = await self._call_with_retries(
                    provider, messages, self._completion_max_retries, self._completion_backoff_base_ms
                )
                return ProviderResult(text=text, provider=provider.name)
            except ProviderError as exc:
                logger.error("provider %s exhausted retries: %s", provider.name, exc)

        text = await self._mock_provider.generate(messages)
        return ProviderResult(text=text, provider=self._mock_provider.name)

    @staticmethod
    async def _call_with_retries(
        provider: BaseLLMProvider, messages: list[dict], max_retries: int, backoff_base_ms: int
    ) -> str:
        last_error: ProviderError | None = None
        for attempt in range(max_retries + 1):
            try:
                return await provider.generate(messages)
            except ProviderError as exc:
                last_error = exc
                logger.warning(
                    "provider %s failed (attempt %d/%d): %s",
                    provider.name, attempt + 1, max_retries + 1, exc,
                )
                if attempt < max_retries and backoff_base_ms:
                    await asyncio.sleep(backoff_base_ms * (attempt + 1) / 1000)
        raise last_error
