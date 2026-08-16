"""Resolves which context is sent to the LLM for a given intent: applies
primary/secondary/degraded rules from personalization.yaml and determines
confidence. Deliberately knows nothing about language, tone, or LLM prompts -
see personalization.py for how this composes with the rest of the result."""

import logging

from src.config.business_config import PersonalizationConfig, SubscriptionRule
from src.models.internal_models import Confidence, ContextResolution, FetchResult

logger = logging.getLogger(__name__)


class ContextResolver:
    def __init__(self, config: PersonalizationConfig):
        self._config = config

    def resolve(self, intent: str, fetch_result: FetchResult, subscription: SubscriptionRule) -> ContextResolution:
        rule = self._config.intents[intent]

        primary_failed = self._any_service_failed(rule.primaryContext, fetch_result)
        secondary_failed = self._any_service_failed(rule.secondaryContext, fetch_result)

        if primary_failed:
            confidence: Confidence = "LOW"
            paths = rule.degradedFallbackContext
        else:
            confidence = "MEDIUM" if secondary_failed else "HIGH"
            paths = list(rule.primaryContext)
            if subscription.allowSecondaryContext:
                paths += rule.secondaryContext

        return ContextResolution(
            selected_context=self._resolve_paths(paths, fetch_result),
            excluded_paths=rule.exclude,
            confidence=confidence,
        )

    @staticmethod
    def _any_service_failed(paths: list[str], fetch_result: FetchResult) -> bool:
        return any(path.split(".")[0] in fetch_result.failed_services for path in paths)

    def _resolve_paths(self, paths: list[str], fetch_result: FetchResult) -> dict[str, object]:
        resolved: dict[str, object] = {}
        for path in paths:
            value = self._resolve_path(path, fetch_result.data)
            if value is None:
                logger.debug("context path unavailable: %s", path)
            else:
                resolved[path] = value
        return resolved

    @staticmethod
    def _resolve_path(path: str, data: dict) -> object | None:
        value: object = data
        for segment in path.split("."):
            if not isinstance(value, dict) or segment not in value:
                return None
            value = value[segment]
        return value
