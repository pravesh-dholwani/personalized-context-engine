"""POST /debug/personalization - runs the pipeline through context
resolution and returns the reasoning behind it, without ever generating
an answer."""

import logging

from fastapi import APIRouter, Depends

from src.api.dependencies import get_business_config, get_engine, get_fetcher
from src.clients.upstream_fetcher import UpstreamFetcher
from src.config.business_config import PersonalizationConfig
from src.engine.personalization import PersonalizationEngine
from src.models.api_schemas import DebugResponse, PersonalizeRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/debug/personalization", response_model=DebugResponse)
async def debug_personalization(
    request: PersonalizeRequest,
    fetcher: UpstreamFetcher = Depends(get_fetcher),
    engine: PersonalizationEngine = Depends(get_engine),
    config: PersonalizationConfig = Depends(get_business_config),
) -> DebugResponse:
    fetch_result = await fetcher.fetch_all(request.userId)
    user = fetch_result.data.get("User", {})

    result = await engine.evaluate(request.question, user, fetch_result)

    logger.info(
        "user_id=%s endpoint=/debug/personalization intent=%s intent_source=%s status=200",
        request.userId, result.intent, result.intent_source,
    )

    return DebugResponse(
        intent=result.intent,
        intentSource=result.intent_source,
        language=result.language,
        tone=result.tone,
        selectedContext=[config.label_for(path) for path in result.selected_context],
        excludedContext=[config.label_for(path) for path in result.excluded_paths],
        confidence=result.confidence,
    )
