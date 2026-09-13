import logging

from arq.connections import RedisSettings
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models import Product, StockAlert

logger = logging.getLogger(__name__)


async def process_low_stock_alert(ctx: dict[str, object], product_id: int, quantity: int) -> str:
    del ctx
    settings = get_settings()
    async with SessionFactory() as session:
        product = await session.get(Product, product_id)
        if product is None or product.stock_quantity >= settings.low_stock_threshold:
            logger.info("low_stock_alert_cancelled", extra={"product_id": product_id})
            return "cancelled"
        job_id = f"low-stock:{product_id}:{product.updated_at.isoformat() if product.updated_at else quantity}"
        session.add(StockAlert(job_id=job_id, product_id=product_id, observed_quantity=product.stock_quantity))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.info("low_stock_alert_duplicate", extra={"product_id": product_id})
            return "duplicate"
        logger.info("low_stock_alert_recorded", extra={"product_id": product_id, "quantity": product.stock_quantity})
    return "recorded"


class WorkerSettings:
    functions = (process_low_stock_alert,)
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    job_timeout = 30
