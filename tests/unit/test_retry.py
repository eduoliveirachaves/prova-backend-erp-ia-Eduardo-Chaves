import asyncio

import pytest

from app.services.dashboard_service import (
    SourceTimeoutError,
    call_with_retry,
)


@pytest.mark.asyncio
async def test_call_with_retry_recovers_after_transient_failure() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary")
        return "ok"

    assert await call_with_retry(operation, timeout=0.05, max_attempts=2, backoff=0) == "ok"
    assert attempts == 2


@pytest.mark.asyncio
async def test_call_with_retry_turns_timeout_into_domain_error() -> None:
    async def operation() -> None:
        await asyncio.sleep(0.1)

    with pytest.raises(SourceTimeoutError):
        await call_with_retry(operation, timeout=0.01, max_attempts=2, backoff=0)
