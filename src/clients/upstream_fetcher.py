"""Fetches all upstream services concurrently and tracks per-service health,
so the engine can operate on partial data instead of all-or-nothing."""

import asyncio
import logging

import httpx
from cachetools import TTLCache

from src.clients.base_client import ServiceClient, UpstreamServiceError
from src.config.tech_config import Settings
from src.models.internal_models import FetchResult

logger = logging.getLogger(__name__)

# (service name, settings attribute holding its base URL, whether it takes a userId)
_SERVICES: list[tuple[str, str, bool]] = [
    ("User", "user_service_url", True),
    ("Kundli", "kundli_service_url", True),
    ("Horoscope", "horoscope_service_url", True),
    ("Panchang", "panchang_service_url", False),
]


class UpstreamFetcher:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient):
        self._settings = settings
        self._service_client = ServiceClient(
            http_client, settings.http_timeout_seconds, settings.http_max_retries
        )
        self._cache: TTLCache = TTLCache(maxsize=256, ttl=settings.cache_ttl_seconds)

    async def fetch_all(self, user_id: str) -> FetchResult:
        results = await asyncio.gather(
            *(self._fetch_one(name, url_attr, needs_user_id, user_id)
              for name, url_attr, needs_user_id in _SERVICES)
        )

        data: dict[str, dict] = {}
        healthy: list[str] = []
        failed: list[str] = []
        for name, payload in results:
            if payload is None:
                failed.append(name)
            else:
                data[name] = payload
                healthy.append(name)

        return FetchResult(data=data, healthy_services=healthy, failed_services=failed)

    async def _fetch_one(
        self, name: str, url_attr: str, needs_user_id: bool, user_id: str
    ) -> tuple[str, dict | None]:
        cache_key = f"{name}:{user_id}" if needs_user_id else name
        cached = self._cache.get(cache_key)
        if cached is not None:
            return name, cached

        base_url = getattr(self._settings, url_attr)
        url = f"{base_url}/{user_id}" if needs_user_id else base_url
        try:
            payload = await self._service_client.get_json(url)
        except UpstreamServiceError as exc:
            logger.error("service unavailable: %s (%s)", name, exc)
            return name, None

        self._cache[cache_key] = payload
        return name, payload
