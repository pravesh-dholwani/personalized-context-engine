"""End-to-end API tests via FastAPI's TestClient with dependency overrides -
no live upstream services or LLM calls.

Covers plan test-matrix rows: Normal Path, Dry-Run Inspection.
"""

import json

import pytest
from fastapi.testclient import TestClient

from mocks.fixtures import HOROSCOPE, KUNDLI, PANCHANG, USER
from src.api.dependencies import (
    get_business_config,
    get_engine,
    get_fetcher,
    get_gateway,
    get_prompt_builder,
    get_prompt_registry,
)
from src.engine.analyzer import QuestionAnalyzer
from src.engine.context_resolver import ContextResolver
from src.engine.personalization import PersonalizationEngine
from src.engine.prompt_builder import PromptBuilder
from src.main import app
from src.models.internal_models import FetchResult, ProviderResult


class _FakeFetcher:
    async def fetch_all(self, user_id: str) -> FetchResult:
        return FetchResult(
            data={"User": USER, "Kundli": KUNDLI, "Horoscope": HOROSCOPE, "Panchang": PANCHANG},
            healthy_services=["User", "Kundli", "Horoscope", "Panchang"],
            failed_services=[],
        )


class _FakeGateway:
    async def classify(self, messages: list[dict]) -> str:
        return json.dumps({"intent": "career", "language": "en", "tone": "motivational"})

    async def complete(self, messages: list[dict]) -> ProviderResult:
        return ProviderResult(text="a grounded reading", provider="mock")


@pytest.fixture
def client():
    config = get_business_config()
    prompts = get_prompt_registry()
    gateway = _FakeGateway()

    app.dependency_overrides[get_fetcher] = lambda: _FakeFetcher()
    app.dependency_overrides[get_gateway] = lambda: gateway
    app.dependency_overrides[get_engine] = lambda: PersonalizationEngine(
        QuestionAnalyzer(gateway, prompts, config), ContextResolver(config), config
    )
    app.dependency_overrides[get_prompt_builder] = lambda: PromptBuilder(prompts, config)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_personalize_returns_grounded_answer_with_sources(client):
    response = client.post("/personalize", json={"userId": "user_101", "question": "Should I switch jobs?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "a grounded reading"
    assert body["confidence"] == "HIGH"
    assert body["failedServices"] == []
    assert "Career Horoscope" in body["sourcesUsed"]
    assert "10th House" in body["sourcesUsed"]


def test_debug_endpoint_never_calls_completion(client, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("complete() should never be called by /debug/personalization")

    monkeypatch.setattr(_FakeGateway, "complete", fail_if_called)

    response = client.post("/debug/personalization", json={"userId": "user_101", "question": "Should I switch jobs?"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "career"
    assert body["intentSource"] == "llm"
    assert "Relationship Horoscope" in body["excludedContext"]
