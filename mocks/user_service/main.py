"""Mock User Service - mirrors GET /users/{userId} from the assignment brief."""

from fastapi import FastAPI

from mocks.common import maybe_fail_or_delay
from mocks.fixtures import USER

app = FastAPI(title="Mock User Service")


@app.get("/users/{user_id}")
async def get_user(user_id: str, fail: bool = False, delayMs: int = 0) -> dict:
    await maybe_fail_or_delay(fail, delayMs)
    return {**USER, "id": user_id}
