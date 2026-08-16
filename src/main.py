"""Application entrypoint: wires the FastAPI app, lifespan-managed HTTP
client, request-id middleware, and route registration."""

import logging
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request

from src.api.routes_debug import router as debug_router
from src.api.routes_main import router as main_router
from src.clients.upstream_fetcher import UpstreamFetcher
from src.config.tech_config import get_settings
from src.observability import configure_logging, set_request_id

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set - completions will use the mock provider")

    async with httpx.AsyncClient() as http_client:
        app.state.fetcher = UpstreamFetcher(settings, http_client)
        yield


app = FastAPI(title="MyNaksh Personalized AI Context Engine", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    set_request_id(uuid.uuid4().hex[:8])
    return await call_next(request)


app.include_router(main_router)
app.include_router(debug_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
