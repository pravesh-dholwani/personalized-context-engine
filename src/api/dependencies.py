"""FastAPI dependency providers. Config/prompt/gateway/engine objects are
cheap and stateless once loaded, so they're memoized as singletons; the
UpstreamFetcher owns an httpx.AsyncClient tied to the app lifespan and is
read from app.state instead (see main.py)."""

from functools import lru_cache

from fastapi import Request

from src.clients.upstream_fetcher import UpstreamFetcher
from src.config.business_config import PersonalizationConfig, load_personalization_config
from src.config.prompt_registry import PromptRegistry, load_prompt_registry
from src.config.tech_config import get_settings
from src.engine.analyzer import QuestionAnalyzer
from src.engine.context_resolver import ContextResolver
from src.engine.personalization import PersonalizationEngine
from src.engine.prompt_builder import PromptBuilder
from src.llm.gateway import LLMGateway


def get_business_config() -> PersonalizationConfig:
    return load_personalization_config()


def get_prompt_registry() -> PromptRegistry:
    return load_prompt_registry()


@lru_cache
def get_gateway() -> LLMGateway:
    return LLMGateway(get_settings())


@lru_cache
def get_analyzer() -> QuestionAnalyzer:
    return QuestionAnalyzer(get_gateway(), get_prompt_registry(), get_business_config())


@lru_cache
def get_resolver() -> ContextResolver:
    return ContextResolver(get_business_config())


@lru_cache
def get_engine() -> PersonalizationEngine:
    return PersonalizationEngine(get_analyzer(), get_resolver(), get_business_config())


@lru_cache
def get_prompt_builder() -> PromptBuilder:
    return PromptBuilder(get_prompt_registry(), get_business_config())


def get_fetcher(request: Request) -> UpstreamFetcher:
    return request.app.state.fetcher
