"""Mock Horoscope Service - mirrors GET /horoscope/{userId} from the assignment brief."""

from fastapi import FastAPI

from mocks.common import maybe_fail_or_delay
from mocks.fixtures import HOROSCOPE

app = FastAPI(title="Mock Horoscope Service")


@app.get("/horoscope/{user_id}")
async def get_horoscope(user_id: str, fail: bool = False, delayMs: int = 0) -> dict:
    await maybe_fail_or_delay(fail, delayMs)
    return HOROSCOPE
