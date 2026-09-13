from typing import Any

import pytest

from app.core.cache import get_json, invalidate, set_json


class UnavailableRedis:
    async def get(self, _key: str) -> str | None:
        raise ConnectionError("redis unavailable")

    async def set(self, *_args: Any, **_kwargs: Any) -> None:
        raise ConnectionError("redis unavailable")

    async def delete(self, _key: str) -> None:
        raise ConnectionError("redis unavailable")


@pytest.mark.asyncio
async def test_cache_failure_does_not_break_database_fallback() -> None:
    redis = UnavailableRedis()

    assert await get_json(redis, "product:v1:1") is None
    await set_json(redis, "product:v1:1", {"id": 1}, ttl=30)
    await invalidate(redis, "product:v1:1")
