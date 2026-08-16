"""ContextResolver + PersonalizationEngine: intent-driven context selection
and subscription-tier personalization.

Covers plan test-matrix rows: Career/Relationship/Health/Finance/General
Intent, Context Exclusion, Free User, Premium User.
"""

import pytest

from src.engine.analyzer import QuestionAnalyzer
from src.engine.context_resolver import ContextResolver
from src.engine.personalization import PersonalizationEngine

_EXPECTED_CONTEXT_BY_INTENT = {
    "career": (
        {"Kundli.houses.10", "Horoscope.career", "Kundli.currentDasha", "Panchang"},
        ["Horoscope.relationship", "Horoscope.health", "Kundli.houses.7"],
    ),
    "relationship": (
        {"Kundli.houses.7", "Horoscope.relationship", "Kundli.moonSign", "Kundli.currentDasha"},
        ["Horoscope.career", "Horoscope.finance", "Kundli.houses.10"],
    ),
    "health": (
        {"Kundli.houses.6", "Horoscope.health", "Kundli.moonSign", "Panchang"},
        ["Horoscope.relationship", "Horoscope.career"],
    ),
    "finance": (
        {"Horoscope.finance", "Kundli.currentDasha", "Kundli.houses.10"},
        ["Horoscope.relationship", "Horoscope.health"],
    ),
    "general": ({"User", "Horoscope", "Kundli.currentDasha", "Panchang"}, []),
}


@pytest.mark.parametrize("intent", _EXPECTED_CONTEXT_BY_INTENT.keys())
def test_resolves_configured_context_for_premium_user(business_config, healthy_fetch_result, intent):
    resolver = ContextResolver(business_config)
    premium = business_config.subscription_for("premium")
    expected_selected, expected_excluded = _EXPECTED_CONTEXT_BY_INTENT[intent]

    resolution = resolver.resolve(intent, healthy_fetch_result, premium)

    assert set(resolution.selected_context.keys()) == expected_selected
    assert resolution.excluded_paths == expected_excluded
    assert resolution.confidence == "HIGH"


def test_free_tier_excludes_secondary_context(business_config, healthy_fetch_result):
    resolver = ContextResolver(business_config)
    free = business_config.subscription_for("free")

    resolution = resolver.resolve("career", healthy_fetch_result, free)

    assert set(resolution.selected_context.keys()) == {"Kundli.houses.10", "Horoscope.career"}


def test_excluded_context_never_appears_in_selection(business_config, healthy_fetch_result):
    resolver = ContextResolver(business_config)
    premium = business_config.subscription_for("premium")

    resolution = resolver.resolve("career", healthy_fetch_result, premium)

    assert not set(resolution.selected_context.keys()) & set(resolution.excluded_paths)


async def test_premium_user_gets_secondary_context_and_follow_up(
    fake_gateway, business_config, prompt_registry, healthy_fetch_result
):
    engine = PersonalizationEngine(
        QuestionAnalyzer(fake_gateway(intent="career"), prompt_registry, business_config),
        ContextResolver(business_config),
        business_config,
    )
    user = {**healthy_fetch_result.data["User"], "subscription": "premium"}

    result = await engine.evaluate("Should I switch jobs?", user, healthy_fetch_result)

    assert result.max_words == 350
    assert result.show_follow_up is True
    assert "Kundli.currentDasha" in result.selected_context


async def test_free_user_gets_restricted_length_and_no_follow_up(
    fake_gateway, business_config, prompt_registry, healthy_fetch_result
):
    engine = PersonalizationEngine(
        QuestionAnalyzer(fake_gateway(intent="career"), prompt_registry, business_config),
        ContextResolver(business_config),
        business_config,
    )
    user = {**healthy_fetch_result.data["User"], "subscription": "free"}

    result = await engine.evaluate("Should I switch jobs?", user, healthy_fetch_result)

    assert result.max_words == 150
    assert result.show_follow_up is False
    assert "Kundli.currentDasha" not in result.selected_context
