"""Shared fixtures. Reuses the mock services' fixture data so tests reflect
the same shapes a live run would see."""

import json

import pytest

from mocks.fixtures import HOROSCOPE, KUNDLI, PANCHANG, USER
from src.config.business_config import load_personalization_config
from src.config.prompt_registry import load_prompt_registry
from src.models.internal_models import FetchResult


class FakeGateway:
    """Stands in for LLMGateway in analyzer/engine tests - only implements
    the classify() method the analyzer actually calls. Builds a realistic
    JSON detection payload from (intent, language_code, tone) so most tests
    don't need to hand-write JSON; pass raw_classify_result directly to test
    malformed/unusual LLM output."""

    def __init__(
        self,
        intent: str | None = None,
        language_code: str = "en",
        tone: str = "neutral",
        classify_error: Exception | None = None,
        raw_classify_result: str | None = None,
    ):
        self._classify_error = classify_error
        if raw_classify_result is not None:
            self._classify_result = raw_classify_result
        elif intent is not None:
            self._classify_result = json.dumps({"intent": intent, "language": language_code, "tone": tone})
        else:
            self._classify_result = None

    async def classify(self, messages: list[dict]) -> str:
        if self._classify_error:
            raise self._classify_error
        return self._classify_result


@pytest.fixture
def fake_gateway():
    return FakeGateway


@pytest.fixture
def business_config():
    return load_personalization_config()


@pytest.fixture
def prompt_registry():
    return load_prompt_registry()


@pytest.fixture
def healthy_fetch_result():
    return FetchResult(
        data={"User": USER, "Kundli": KUNDLI, "Horoscope": HOROSCOPE, "Panchang": PANCHANG},
        healthy_services=["User", "Kundli", "Horoscope", "Panchang"],
        failed_services=[],
    )


@pytest.fixture
def kundli_down_fetch_result():
    return FetchResult(
        data={"User": USER, "Horoscope": HOROSCOPE, "Panchang": PANCHANG},
        healthy_services=["User", "Horoscope", "Panchang"],
        failed_services=["Kundli"],
    )
