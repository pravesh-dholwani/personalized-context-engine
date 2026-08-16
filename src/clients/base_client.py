"""Thin async HTTP wrapper: timeout + retry collapsed into one failure type
so callers don't need to know about httpx's exception hierarchy."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_RETRY_DELAY_SECONDS = 0.1


class UpstreamServiceError(Exception):
    """Raised when a URL could not be fetched after all retries."""


class ServiceClient:
    def __init__(self, http_client: httpx.AsyncClient, timeout_seconds: float, max_retries: int):
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    async def get_json(self, url: str) -> dict:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._http_client.get(url, timeout=self._timeout_seconds)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    raise UpstreamServiceError(f"{url} returned {exc.response.status_code}") from exc
                last_error = exc
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc

            logger.warning(
                "upstream call failed url=%s attempt=%d/%d error=%s",
                url, attempt + 1, self._max_retries + 1, last_error,
            )
            if attempt < self._max_retries:
                await asyncio.sleep(_RETRY_DELAY_SECONDS)

        raise UpstreamServiceError(f"{url} failed after {self._max_retries + 1} attempts") from last_error
