from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.repositories import product_repository


class ProductNotFoundError(LookupError):
    pass


async def create(session: AsyncSession, *, name: str, price: Decimal, stock_quantity: int) -> Product:
    return await product_repository.create_product(session, name=name, price=price, stock_quantity=stock_quantity)


async def get(session: AsyncSession, product_id: int) -> Product:
    product = await product_repository.get_product(session, product_id)
    if product is None:
        raise ProductNotFoundError(product_id)
    return product


async def update(session: AsyncSession, product_id: int, *, name: str, price: Decimal, stock_quantity: int) -> Product:
    product = await get(session, product_id)
    return await product_repository.update_product(
        session, product, name=name, price=price, stock_quantity=stock_quantity
    )


async def remove(session: AsyncSession, product_id: int) -> None:
    product = await get(session, product_id)
    await product_repository.delete_product(session, product)


async def list_low_stock(session: AsyncSession, *, max_quantity: int) -> list[Product]:
    products, _ = await product_repository.list_products(
        session,
        page=1,
        page_size=100,
        max_stock=max_quantity,
    )
    return products
