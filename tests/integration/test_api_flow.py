import asyncio
import os
import uuid

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import select

from app.core.cache import product_key
from app.db.session import SessionFactory
from app.models import StockAlert

API_URL = os.getenv("API_URL")
pytestmark = pytest.mark.skipif(API_URL is None, reason="requires the Docker Compose stack")


async def wait_for_stock_alert(product_id: int) -> StockAlert:
    for _ in range(20):
        async with SessionFactory() as session:
            alert = await session.scalar(select(StockAlert).where(StockAlert.product_id == product_id))
            if alert is not None:
                return alert
        await asyncio.sleep(0.25)
    raise AssertionError("stock alert was not processed")


@pytest.mark.asyncio
async def test_evaluation_flow() -> None:
    assert API_URL is not None
    redis = Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    product_id: int | None = None

    try:
        async with httpx.AsyncClient(base_url=API_URL, timeout=5) as client:
            unauthorized = await client.get("/api/v1/products")
            assert unauthorized.status_code == 401

            token_response = await client.post(
                "/api/v1/auth/token",
                data={
                    "username": os.environ["DEMO_USERNAME"],
                    "password": os.environ["DEMO_PASSWORD"],
                },
            )
            token_response.raise_for_status()
            headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

            product_name = f"Integration product {uuid.uuid4().hex[:8]}"
            create_response = await client.post(
                "/api/v1/products",
                headers=headers,
                json={"name": product_name, "price": "99.90", "stock_quantity": 4},
            )
            assert create_response.status_code == 201
            product_id = create_response.json()["id"]

            read_response = await client.get(f"/api/v1/products/{product_id}", headers=headers)
            assert read_response.status_code == 200
            assert read_response.json()["name"] == product_name
            assert await redis.get(product_key(product_id)) is not None

            list_response = await client.get(
                "/api/v1/products",
                headers=headers,
                params={"name": product_name, "low_stock": "true"},
            )
            assert list_response.status_code == 200
            assert list_response.json()["total"] == 1

            update_response = await client.put(
                f"/api/v1/products/{product_id}",
                headers=headers,
                json={"name": product_name, "price": "109.90", "stock_quantity": 3},
            )
            assert update_response.status_code == 200
            assert await redis.get(product_key(product_id)) is None

            dashboard_response = await client.get(
                f"/api/v1/dashboard/{product_id}",
                headers=headers,
                params={"scenario": "degraded"},
            )
            assert dashboard_response.status_code == 200
            dashboard = dashboard_response.json()
            assert dashboard["stock"]["status"] == "ok"
            assert dashboard["customer"]["status"] == "timeout"
            assert dashboard["financial"]["status"] == "ok"
            assert dashboard["financial"]["attempts"] == 2

            agent_response = await client.post(
                "/api/v1/agent/query",
                headers=headers,
                json={"question": "Quais produtos estão com estoque abaixo de 10 unidades?"},
            )
            assert agent_response.status_code == 200
            agent_result = agent_response.json()
            assert agent_result["tool_call"] == {
                "name": "find_low_stock",
                "arguments": {"max_quantity": 10},
            }
            assert product_id in {item["id"] for item in agent_result["result"]}

            unsupported_agent_response = await client.post(
                "/api/v1/agent/query",
                headers=headers,
                json={"question": "Crie um pedido para o cliente 42"},
            )
            assert unsupported_agent_response.status_code == 422

            alert = await wait_for_stock_alert(product_id)
            assert alert.observed_quantity in {3, 4}

            delete_response = await client.delete(f"/api/v1/products/{product_id}", headers=headers)
            assert delete_response.status_code == 204
            missing_response = await client.get(f"/api/v1/products/{product_id}", headers=headers)
            assert missing_response.status_code == 404
            product_id = None
    finally:
        if product_id is not None:
            async with httpx.AsyncClient(base_url=API_URL, timeout=5) as client:
                token_response = await client.post(
                    "/api/v1/auth/token",
                    data={
                        "username": os.environ["DEMO_USERNAME"],
                        "password": os.environ["DEMO_PASSWORD"],
                    },
                )
                if token_response.is_success:
                    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
                    await client.delete(f"/api/v1/products/{product_id}", headers=headers)
        await redis.aclose()
