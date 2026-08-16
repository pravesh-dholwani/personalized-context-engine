"""Shared fault-injection helper for the mock upstream services, so manual
testing and the automated test suite can exercise degraded/timeout paths
without a real backend outage."""

import asyncio

from fastapi import HTTPException


async def maybe_fail_or_delay(fail: bool, delay_ms: int) -> None:
    if delay_ms:
        await asyncio.sleep(delay_ms / 1000)
    if fail:
        raise HTTPException(status_code=503, detail="simulated upstream failure")
