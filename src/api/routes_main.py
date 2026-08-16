"""POST /personalize - fetch context, personalize, and generate a grounded,
sourced answer."""

import logging
import re

from fastapi import APIRouter, Depends

from src.api.dependencies import (
    get_business_config,
    get_engine,
    get_fetcher,
    get_gateway,
    get_prompt_builder,
)
from src.clients.upstream_fetcher import UpstreamFetcher
from src.config.business_config import PersonalizationConfig
from src.engine.personalization import PersonalizationEngine
from src.engine.prompt_builder import PromptBuilder
from src.llm.gateway import LLMGateway
from src.models.api_schemas import PersonalizeRequest, PersonalizeResponse
from src.observability import timer

logger = logging.getLogger(__name__)
router = APIRouter()

# The follow-up instruction (prompts.yaml) asks the LLM to end its answer
# with "Follow-up: <question>" - split that back out into its own field.
_FOLLOW_UP_PATTERN = re.compile(r"\n*Follow-up:\s*(.+)", re.IGNORECASE | re.DOTALL)


@router.post("/personalize", response_model=PersonalizeResponse)
async def personalize(
    request: PersonalizeRequest,
    fetcher: UpstreamFetcher = Depends(get_fetcher),
    engine: PersonalizationEngine = Depends(get_engine),
    prompt_builder: PromptBuilder = Depends(get_prompt_builder),
    gateway: LLMGateway = Depends(get_gateway),
    config: PersonalizationConfig = Depends(get_business_config),
) -> PersonalizeResponse:
    with timer() as fetch_ms:
        fetch_result = await fetcher.fetch_all(request.userId)
    user = fetch_result.data.get("User", {})

    result = await engine.evaluate(request.question, user, fetch_result)
    messages = prompt_builder.build_messages(result, request.question)

    with timer() as llm_ms:
        provider_result = await gateway.complete(messages)

    answer, follow_up = _split_follow_up(provider_result.text)
    prompt_chars = sum(len(m["content"]) for m in messages)

    logger.info(
        "user_id=%s endpoint=/personalize intent=%s status=200 confidence=%s provider=%s "
        "prompt_chars=%d fetch_ms=%.0f llm_ms=%.0f total_ms=%.0f",
        request.userId, result.intent, result.confidence, provider_result.provider,
        prompt_chars, fetch_ms(), llm_ms(), fetch_ms() + llm_ms(),
    )

    return PersonalizeResponse(
        answer=answer,
        confidence=result.confidence,
        sourcesUsed=[config.label_for(path) for path in result.selected_context],
        followUpQuestion=follow_up,
        failedServices=result.failed_services,
    )


def _split_follow_up(text: str) -> tuple[str, str | None]:
    match = _FOLLOW_UP_PATTERN.search(text)
    if not match:
        return text.strip(), None
    return text[: match.start()].strip(), match.group(1).strip()
