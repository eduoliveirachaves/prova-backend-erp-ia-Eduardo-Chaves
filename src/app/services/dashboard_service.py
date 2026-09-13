import asyncio
from collections.abc import Awaitable, Callable


class SourceTimeoutError(TimeoutError):
    pass


async def call_with_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    timeout: float = 0.5,
    max_attempts: int = 2,
    backoff: float = 0.05,
) -> T:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await asyncio.wait_for(operation(), timeout=timeout)
        except TimeoutError:
            last_error = SourceTimeoutError(f"source timed out after {timeout:.3f}s")
        except Exception as exc:
            last_error = exc
        if attempt < max_attempts:
            await asyncio.sleep(backoff * attempt)
    assert last_error is not None
    raise last_error
