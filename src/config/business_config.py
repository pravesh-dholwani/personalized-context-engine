"""Tier 2 config: business rules loaded from personalization.yaml.

This is what makes the personalization engine configuration-driven -
adding a new intent means adding a YAML entry here, not editing the
resolver's code.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

ResolutionStrategy = Literal["question_first", "profile_first"]


class ResponseRules(BaseModel):
    languageStrategy: ResolutionStrategy
    toneStrategy: ResolutionStrategy


class SubscriptionRule(BaseModel):
    allowSecondaryContext: bool
    maxOutputWords: int
    showFollowUpQuestion: bool


class IntentRule(BaseModel):
    keywords: list[str]
    primaryContext: list[str]
    secondaryContext: list[str]
    degradedFallbackContext: list[str]
    exclude: list[str]


class DegradationRules(BaseModel):
    confidenceOnSecondaryFailure: str
    confidenceOnPrimaryFailure: str


class PersonalizationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    responseRules: ResponseRules
    languageMap: dict[str, str]
    contextLabels: dict[str, str]
    subscriptionRules: dict[str, SubscriptionRule]
    intents: dict[str, IntentRule]
    degradationRules: DegradationRules

    def label_for(self, path: str) -> str:
        return self.contextLabels.get(path, path)

    def language_for(self, code: str) -> str:
        return self.languageMap.get(code, self.languageMap["default"])

    def language_codes(self) -> list[str]:
        """Supported codes, excluding the 'default' fallback entry - used to
        tell the LLM classifier which codes it's allowed to return."""
        return [code for code in self.languageMap if code != "default"]

    def subscription_for(self, tier: str) -> SubscriptionRule:
        return self.subscriptionRules.get(tier, self.subscriptionRules["free"])

    def intent_names(self) -> list[str]:
        return list(self.intents.keys())


@lru_cache
def load_personalization_config(path: str = "config/personalization.yaml") -> PersonalizationConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return PersonalizationConfig(**raw)
