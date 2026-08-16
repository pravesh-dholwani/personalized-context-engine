"""Internal engine contracts - never serialized directly to a client.
Keeping these separate from api_schemas.py means the engine's internal
shape can evolve without touching the public API contract.
"""

from typing import Literal

from pydantic import BaseModel

Confidence = Literal["HIGH", "MEDIUM", "LOW"]
IntentSource = Literal["llm", "keyword"]


class FetchResult(BaseModel):
    data: dict[str, dict]
    healthy_services: list[str]
    failed_services: list[str]


class QuestionAnalysis(BaseModel):
    intent: str
    source: IntentSource
    language: str
    tone: str


class ContextResolution(BaseModel):
    """The ContextResolver's own output - deliberately narrower than
    PersonalizationResult, matching the plan's Context Resolution Example
    (selectedContext/excludedContext/confidence only, no language/tone)."""

    selected_context: dict[str, object]
    excluded_paths: list[str]
    confidence: Confidence


class PersonalizationResult(BaseModel):
    intent: str
    intent_source: IntentSource
    language: str
    tone: str
    max_words: int
    show_follow_up: bool
    selected_context: dict[str, object]
    excluded_paths: list[str]
    confidence: Confidence
    failed_services: list[str]


class ProviderResult(BaseModel):
    text: str
    provider: str
