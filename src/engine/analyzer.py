"""Detects intent, language, and tone from the question text via a single
LLM call, with keyword matching and the user profile as deterministic
fallbacks if that call fails or returns something unusable."""

import json
import logging
import re
from dataclasses import dataclass

from src.config.business_config import PersonalizationConfig, ResolutionStrategy
from src.config.prompt_registry import PromptRegistry
from src.llm.base_provider import ProviderError
from src.llm.gateway import LLMGateway
from src.models.internal_models import QuestionAnalysis

logger = logging.getLogger(__name__)

# LLMs sometimes wrap JSON in a markdown fence despite being told not to.
_CODE_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass
class _Detected:
    intent: str
    language_code: str
    tone: str


class QuestionAnalyzer:
    def __init__(self, gateway: LLMGateway, prompts: PromptRegistry, config: PersonalizationConfig):
        self._gateway = gateway
        self._prompts = prompts
        self._config = config

    async def analyze(self, question: str, user: dict) -> QuestionAnalysis:
        detected = await self._detect(question)
        rules = self._config.responseRules

        return QuestionAnalysis(
            intent=detected.intent if detected else self._match_keywords(question),
            source="llm" if detected else "keyword",
            language=self._resolve_language(detected, user, rules.languageStrategy),
            tone=self._resolve_tone(detected, user, rules.toneStrategy),
        )

    async def _detect(self, question: str) -> _Detected | None:
        system_prompt = self._prompts.system_prompt_for("intent_classifier").format(
            valid_languages=", ".join(self._config.language_codes())
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._prompts.user_prompts["intent_classifier"].format(question=question)},
        ]

        try:
            raw = await self._gateway.classify(messages)
        except ProviderError as exc:
            logger.warning("question analysis unavailable, falling back to keywords/profile: %s", exc)
            return None

        detected = self._parse(raw)
        if detected is None or detected.intent not in self._config.intents:
            logger.warning("LLM returned unusable analysis %r, falling back to keywords/profile", raw)
            return None
        return detected

    @staticmethod
    def _parse(raw: str) -> _Detected | None:
        try:
            data = json.loads(_CODE_FENCE.sub("", raw.strip()))
            return _Detected(
                intent=str(data["intent"]).strip().lower(),
                language_code=str(data["language"]).strip().lower(),
                tone=str(data["tone"]).strip(),
            )
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
            return None

    def _resolve_language(self, detected: _Detected | None, user: dict, strategy: ResolutionStrategy) -> str:
        profile_code = user.get("language") or None
        question_code = detected.language_code if detected else None

        code = (question_code or profile_code) if strategy == "question_first" else (profile_code or question_code)
        return self._config.language_for(code or "")

    @staticmethod
    def _resolve_tone(detected: _Detected | None, user: dict, strategy: ResolutionStrategy) -> str:
        profile_tone = user.get("tonePreference") or None
        question_tone = detected.tone if detected else None

        tone = (question_tone or profile_tone) if strategy == "question_first" else (profile_tone or question_tone)
        return (tone or "neutral").capitalize()

    def _match_keywords(self, question: str) -> str:
        question_lower = question.lower()
        for intent_name, rule in self._config.intents.items():
            if any(keyword in question_lower for keyword in rule.keywords):
                return intent_name
        return "general"
