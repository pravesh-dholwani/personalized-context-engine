"""Cross-cutting request logging: request-id propagation and latency timing.

Kept separate from any single layer because every layer (api, clients,
engine, llm) needs to log against the same request-id and timing
conventions.
"""

import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Iterator

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


def configure_logging(level: str = "info") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
    )
    # Filters must live on the handler, not the root logger, so they apply
    # to records propagated up from every module-level logger.
    request_id_filter = _RequestIdFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(request_id_filter)

    # httpx logs one INFO line per outgoing request - redundant with our own
    # structured request/failure logging above it.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def set_request_id(request_id: str) -> None:
    _request_id.set(request_id)


@contextmanager
def timer() -> Iterator[Callable[[], float]]:
    """Yields a callable returning elapsed milliseconds since entry."""
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000
