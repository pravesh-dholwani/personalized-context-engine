"""Mock Panchang Service - mirrors GET /panchang from the assignment brief.
Unlike the other three services, this endpoint takes no userId."""

from fastapi import FastAPI

from mocks.common import maybe_fail_or_delay
from mocks.fixtures import PANCHANG

app = FastAPI(title="Mock Panchang Service")


@app.get("/panchang")
async def get_panchang(fail: bool = False, delayMs: int = 0) -> dict:
    await maybe_fail_or_delay(fail, delayMs)
    return PANCHANG
