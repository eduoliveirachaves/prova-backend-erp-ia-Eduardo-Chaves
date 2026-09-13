import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import current_user
from app.models import User
from app.schemas.dashboard import DashboardResult, SourceResult
from app.services.dashboard_service import SourceTimeoutError, call_with_retry

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


async def source_result(operation: Any) -> SourceResult:
    attempts = 0

    async def counted() -> Any:
        nonlocal attempts
        attempts += 1
        return await operation()

    try:
        data = await call_with_retry(counted)
        return SourceResult(status="ok", attempts=attempts, data=data)
    except SourceTimeoutError as exc:
        return SourceResult(status="timeout", attempts=attempts, error=str(exc))
    except Exception as exc:
        return SourceResult(status="error", attempts=attempts, error=str(exc))


@router.get("/{product_id}", response_model=DashboardResult)
async def dashboard(
    product_id: int,
    scenario: str = Query("success", pattern="^(success|degraded)$"),
    _: User = Depends(current_user),
) -> DashboardResult:
    finance_attempts = 0

    async def stock() -> dict[str, object]:
        await asyncio.sleep(0.01)
        return {"product_id": product_id, "available": max(0, 100 - product_id)}

    async def customer() -> dict[str, object]:
        await asyncio.sleep(0.8 if scenario == "degraded" else 0.01)
        return {"customer_id": product_id, "status": "active"}

    async def financial() -> dict[str, object]:
        nonlocal finance_attempts
        finance_attempts += 1
        await asyncio.sleep(0.01)
        if scenario == "degraded" and finance_attempts == 1:
            raise RuntimeError("financial source temporarily unavailable")
        return {"customer_id": product_id, "status": "clear"}

    stock_result, customer_result, financial_result = await asyncio.gather(
        source_result(stock), source_result(customer), source_result(financial)
    )
    return DashboardResult(
        product_id=product_id,
        stock=stock_result,
        customer=customer_result,
        financial=financial_result,
    )
