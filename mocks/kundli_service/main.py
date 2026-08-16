"""Mock Kundli Service - mirrors GET /kundli/{userId} from the assignment brief."""

from fastapi import FastAPI

from mocks.common import maybe_fail_or_delay
from mocks.fixtures import KUNDLI

app = FastAPI(title="Mock Kundli Service")


@app.get("/kundli/{user_id}")
async def get_kundli(user_id: str, fail: bool = False, delayMs: int = 0) -> dict:
    await maybe_fail_or_delay(fail, delayMs)
    return KUNDLI
