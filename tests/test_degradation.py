"""Graceful degradation: confidence tiering and fallback context when
upstream services are unavailable.

Covers plan test-matrix rows: Partial Upstream Outage, Multiple Upstream
Failures.
"""

from src.engine.context_resolver import ContextResolver
from src.models.internal_models import FetchResult


def test_primary_source_failure_drops_confidence_to_low_and_uses_fallback(business_config, kundli_down_fetch_result):
    resolver = ContextResolver(business_config)
    premium = business_config.subscription_for("premium")

    resolution = resolver.resolve("career", kundli_down_fetch_result, premium)

    assert resolution.confidence == "LOW"
    assert set(resolution.selected_context.keys()) == {"Horoscope.career", "Panchang"}


def test_secondary_source_failure_drops_confidence_to_medium(business_config):
    # Career's primaryContext (Kundli.houses.10, Horoscope.career) is healthy;
    # only Panchang - part of its secondaryContext - is down.
    fetch_result = FetchResult(
        data={"Kundli": {"houses": {"10": {"lord": "Moon", "strength": "Strong"}}}, "Horoscope": {"career": "..."}},
        healthy_services=["Kundli", "Horoscope"],
        failed_services=["Panchang"],
    )
    resolver = ContextResolver(business_config)
    premium = business_config.subscription_for("premium")

    resolution = resolver.resolve("career", fetch_result, premium)

    assert resolution.confidence == "MEDIUM"


def test_multiple_failures_return_empty_context_without_crashing(business_config):
    fetch_result = FetchResult(
        data={}, healthy_services=[], failed_services=["User", "Kundli", "Horoscope", "Panchang"]
    )
    resolver = ContextResolver(business_config)
    premium = business_config.subscription_for("premium")

    resolution = resolver.resolve("career", fetch_result, premium)

    assert resolution.confidence == "LOW"
    assert resolution.selected_context == {}
