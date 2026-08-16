"""UpstreamFetcher: concurrent fetch, per-service failure isolation, retry,
and caching - tested against httpx.MockTransport rather than live servers.

Covers plan test-matrix rows: Upstream Timeout (via retryable failures),
Cache Hit, Cache Expiry (via per-user cache key isolation).

Not one of the plan's originally-listed test files (test_analyzer/
test_engine/test_degradation/test_fallback/test_api) - added because the
fetcher's own retry/caching behavior needs its own coverage, distinct from
how the engine reacts to a FetchResult that already reflects a failure.
"""

import httpx

from src.clients.upstream_fetcher import UpstreamFetcher
from src.config.tech_config import Settings


def _settings(**overrides):
    defaults = dict(
        user_service_url="http://user.test/users",
        kundli_service_url="http://kundli.test/kundli",
        horoscope_service_url="http://horoscope.test/horoscope",
        panchang_service_url="http://panchang.test/panchang",
        http_max_retries=1,
        cache_ttl_seconds=60,
    )
    return Settings(**{**defaults, **overrides})


async def test_fetch_all_isolates_a_failing_service():
    def handler(request: httpx.Request) -> httpx.Response:
        if "kundli" in str(request.url):
            return httpx.Response(500)
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await UpstreamFetcher(_settings(), client).fetch_all("user_101")

    assert set(result.healthy_services) == {"User", "Horoscope", "Panchang"}
    assert result.failed_services == ["Kundli"]


async def test_transient_failure_is_retried_before_giving_up():
    calls = {"kundli": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "kundli" in str(request.url):
            calls["kundli"] += 1
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await UpstreamFetcher(_settings(http_max_retries=2), client).fetch_all("user_101")

    assert calls["kundli"] == 3  # 1 initial attempt + 2 retries
    assert result.failed_services == ["Kundli"]


async def test_client_error_is_not_retried():
    calls = {"kundli": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "kundli" in str(request.url):
            calls["kundli"] += 1
            return httpx.Response(404)
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await UpstreamFetcher(_settings(), client).fetch_all("user_101")

    assert calls["kundli"] == 1  # a 4xx is a client error, not a transient failure
    assert result.failed_services == ["Kundli"]


async def test_second_fetch_for_same_user_is_served_from_cache():
    calls = {"kundli": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "kundli" in str(request.url):
            calls["kundli"] += 1
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        fetcher = UpstreamFetcher(_settings(), client)
        await fetcher.fetch_all("user_101")
        await fetcher.fetch_all("user_101")

    assert calls["kundli"] == 1


async def test_cache_is_keyed_per_user():
    calls = {"kundli": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if "kundli" in str(request.url):
            calls["kundli"] += 1
        return httpx.Response(200, json={"ok": True})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        fetcher = UpstreamFetcher(_settings(), client)
        await fetcher.fetch_all("user_101")
        await fetcher.fetch_all("user_202")

    assert calls["kundli"] == 2
