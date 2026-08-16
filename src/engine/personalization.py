"""The Personalization Engine: combines the analyzer's intent/language/tone
with the context resolver's selection and the user's subscription tier into
one PersonalizationResult. This is the single entry point both /personalize
and /debug/personalization call - they diverge only after this point."""

import logging

from src.config.business_config import PersonalizationConfig
from src.engine.analyzer import QuestionAnalyzer
from src.engine.context_resolver import ContextResolver
from src.models.internal_models import FetchResult, PersonalizationResult
from src.observability import timer

logger = logging.getLogger(__name__)


class PersonalizationEngine:
    def __init__(self, analyzer: QuestionAnalyzer, resolver: ContextResolver, config: PersonalizationConfig):
        self._analyzer = analyzer
        self._resolver = resolver
        self._config = config

    async def evaluate(self, question: str, user: dict, fetch_result: FetchResult) -> PersonalizationResult:
        with timer() as analysis_ms:
            analysis = await self._analyzer.analyze(question, user)

        with timer() as resolution_ms:
            subscription = self._config.subscription_for(user.get("subscription", "free"))
            resolution = self._resolver.resolve(analysis.intent, fetch_result, subscription)

        logger.debug(
            "intent_classification_ms=%.1f context_resolution_ms=%.1f", analysis_ms(), resolution_ms()
        )

        return PersonalizationResult(
            intent=analysis.intent,
            intent_source=analysis.source,
            language=analysis.language,
            tone=analysis.tone,
            max_words=subscription.maxOutputWords,
            show_follow_up=subscription.showFollowUpQuestion,
            selected_context=resolution.selected_context,
            excluded_paths=resolution.excluded_paths,
            confidence=resolution.confidence,
            failed_services=fetch_result.failed_services,
        )
