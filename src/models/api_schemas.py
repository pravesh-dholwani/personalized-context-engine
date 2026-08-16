"""Public API contracts. Nothing outside this module should shape what
crosses the wire - internal engine types (internal_models.py) stay internal.
"""

from pydantic import BaseModel


class PersonalizeRequest(BaseModel):
    userId: str
    question: str


class PersonalizeResponse(BaseModel):
    answer: str
    confidence: str
    sourcesUsed: list[str]
    followUpQuestion: str | None = None
    failedServices: list[str] = []


class DebugResponse(BaseModel):
    intent: str
    intentSource: str
    language: str
    tone: str
    selectedContext: list[str]
    excludedContext: list[str]
    confidence: str
