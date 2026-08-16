"""QuestionAnalyzer: LLM-primary detection (intent + language + tone from
the question text) with keyword/profile fallback.

Covers plan test-matrix rows: Career/Relationship/Health/Finance/General
Intent, Free-Form Question, LLM Classifier Failure, Language Preference,
Tone Preference.
"""

from src.engine.analyzer import QuestionAnalyzer
from src.llm.base_provider import ProviderError


def _profile_first(config):
    """A PersonalizationConfig clone with both strategies flipped to
    profile_first, without needing a second YAML fixture file."""
    from src.config.business_config import ResponseRules

    return config.model_copy(
        update={"responseRules": ResponseRules(languageStrategy="profile_first", toneStrategy="profile_first")}
    )


# --- intent ------------------------------------------------------------


async def test_llm_detects_intent_from_free_form_question(fake_gateway, business_config, prompt_registry):
    analyzer = QuestionAnalyzer(fake_gateway(intent="career"), prompt_registry, business_config)

    analysis = await analyzer.analyze("What should I prioritize to grow professionally?", {})

    assert analysis.intent == "career"
    assert analysis.source == "llm"


async def test_classifier_failure_falls_back_to_keywords(fake_gateway, business_config, prompt_registry):
    analyzer = QuestionAnalyzer(fake_gateway(classify_error=ProviderError("boom")), prompt_registry, business_config)

    analysis = await analyzer.analyze("Should I switch my job this year?", {})

    assert analysis.intent == "career"
    assert analysis.source == "keyword"


async def test_unrecognized_llm_intent_falls_back_to_keywords(fake_gateway, business_config, prompt_registry):
    analyzer = QuestionAnalyzer(fake_gateway(intent="not-a-real-intent"), prompt_registry, business_config)

    analysis = await analyzer.analyze("How does this month look for my relationship?", {})

    assert analysis.intent == "relationship"
    assert analysis.source == "keyword"


async def test_malformed_json_falls_back_to_keywords(fake_gateway, business_config, prompt_registry):
    analyzer = QuestionAnalyzer(
        fake_gateway(raw_classify_result="not json at all"), prompt_registry, business_config
    )

    analysis = await analyzer.analyze("How does this month look for my relationship?", {})

    assert analysis.intent == "relationship"
    assert analysis.source == "keyword"


async def test_markdown_fenced_json_still_parses(fake_gateway, business_config, prompt_registry):
    fenced = '```json\n{"intent": "career", "language": "en", "tone": "Calm"}\n```'
    analyzer = QuestionAnalyzer(fake_gateway(raw_classify_result=fenced), prompt_registry, business_config)

    analysis = await analyzer.analyze("What should I prioritize to grow professionally?", {})

    assert analysis.intent == "career"
    assert analysis.source == "llm"


async def test_keyword_fallback_matches_all_sample_questions(fake_gateway, business_config, prompt_registry):
    analyzer = QuestionAnalyzer(fake_gateway(classify_error=ProviderError("unavailable")), prompt_registry, business_config)
    sample_questions = {
        "Should I consider changing my job this year?": "career",
        "How does this month look for my relationship?": "relationship",
        "What should I focus on for my health?": "health",
        "What should I prioritize this week?": "general",
        "Can you summarize today's guidance?": "general",
    }

    for question, expected_intent in sample_questions.items():
        analysis = await analyzer.analyze(question, {})
        assert analysis.intent == expected_intent, question


# --- language/tone: question_first (the shipped default) ---------------


async def test_question_first_prefers_llm_detection_over_profile(fake_gateway, business_config, prompt_registry):
    analyzer = QuestionAnalyzer(
        fake_gateway(intent="general", language_code="hi", tone="Calm"), prompt_registry, business_config
    )

    analysis = await analyzer.analyze(
        "Can you summarize today's guidance?", {"language": "en", "tonePreference": "motivational"}
    )

    assert analysis.language == "Hindi"
    assert analysis.tone == "Calm"


async def test_question_first_falls_back_to_profile_when_llm_unavailable(fake_gateway, business_config, prompt_registry):
    analyzer = QuestionAnalyzer(fake_gateway(classify_error=ProviderError("boom")), prompt_registry, business_config)

    analysis = await analyzer.analyze(
        "Can you summarize today's guidance?", {"language": "hi", "tonePreference": "calm"}
    )

    assert analysis.language == "Hindi"
    assert analysis.tone == "Calm"


async def test_unknown_detected_language_code_falls_back_to_default(fake_gateway, business_config, prompt_registry):
    analyzer = QuestionAnalyzer(
        fake_gateway(intent="general", language_code="xx", tone="neutral"), prompt_registry, business_config
    )

    analysis = await analyzer.analyze("Can you summarize today's guidance?", {})

    assert analysis.language == "English"


# --- language/tone: profile_first ---------------------------------------


async def test_profile_first_prefers_profile_when_set(fake_gateway, business_config, prompt_registry):
    config = _profile_first(business_config)
    analyzer = QuestionAnalyzer(
        fake_gateway(intent="general", language_code="hi", tone="Calm"), prompt_registry, config
    )

    analysis = await analyzer.analyze(
        "Can you summarize today's guidance?", {"language": "en", "tonePreference": "motivational"}
    )

    assert analysis.language == "English"
    assert analysis.tone == "Motivational"


async def test_profile_first_falls_back_to_question_when_profile_unset(fake_gateway, business_config, prompt_registry):
    config = _profile_first(business_config)
    analyzer = QuestionAnalyzer(
        fake_gateway(intent="general", language_code="hi", tone="Calm"), prompt_registry, config
    )

    analysis = await analyzer.analyze("Can you summarize today's guidance?", {})

    assert analysis.language == "Hindi"
    assert analysis.tone == "Calm"


async def test_neither_source_defaults_to_english_and_neutral(fake_gateway, business_config, prompt_registry):
    config = _profile_first(business_config)
    analyzer = QuestionAnalyzer(fake_gateway(classify_error=ProviderError("boom")), prompt_registry, config)

    analysis = await analyzer.analyze("Can you summarize today's guidance?", {})

    assert analysis.language == "English"
    assert analysis.tone == "Neutral"
