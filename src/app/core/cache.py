import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def product_key(product_id: int) -> str:
    return f"product:v1:{product_id}"


async def get_json(redis: Any, key: str) -> dict[str, Any] | None:
    try:
        value = await redis.get(key)
        return json.loads(value) if value else None
    except Exception:
        logger.warning("cache_read_failed", extra={"key": key}, exc_info=True)
        return None


async def set_json(redis: Any, key: str, value: dict[str, Any], ttl: int) -> None:
    try:
        await redis.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        logger.warning("cache_write_failed", extra={"key": key}, exc_info=True)


async def invalidate(redis: Any, key: str) -> None:
    try:
        await redis.delete(key)
    except Exception:
        logger.warning("cache_invalidation_failed", extra={"key": key}, exc_info=True)
