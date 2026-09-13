import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from arq.connections import RedisSettings
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.routes import agent, auth, dashboard, products
from app.core.config import get_settings
from app.db.session import SessionFactory


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "method", "path", "status_code", "duration_ms", "product_id"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class LazyQueue:
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self.pool: Any | None = None

    async def enqueue_job(self, *args: object, **kwargs: object) -> None:
        if self.pool is None:
            from arq import create_pool

            settings = RedisSettings.from_dsn(self.redis_url)
            settings.conn_timeout = 1
            settings.conn_retries = 0
            self.pool = await create_pool(settings)
        pool: Any = self.pool
        await pool.enqueue_job(*args, **kwargs)

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("erp")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.logger = configure_logging()
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.arq = LazyQueue(settings.redis_url)
    yield
    await app.state.redis.aclose()
    await app.state.arq.close()


app = FastAPI(title="ERP Backend Challenge", version="1.0.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(dashboard.router)
app.include_router(agent.router)


@app.middleware("http")
async def request_logging(request: Request, call_next: Any):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = f"{duration_ms:.2f}"
        return response
    except Exception:
        app.state.logger.exception(
            "http_request_failed",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )
        raise
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        app.state.logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready(request: Request):
    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
        await request.app.state.redis.ping()
    except Exception:
        request.app.state.logger.warning("readiness_check_failed", exc_info=True)
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
