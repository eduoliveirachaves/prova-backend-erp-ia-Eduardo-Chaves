from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models import Product


async def create_product(session: AsyncSession, *, name: str, price: Decimal, stock_quantity: int) -> Product:
    product = Product(name=name, price=price, stock_quantity=stock_quantity)
    session.add(product)
    await session.flush()
    await session.refresh(product)
    return product


async def get_product(session: AsyncSession, product_id: int) -> Product | None:
    return await session.get(Product, product_id)


async def list_products(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    name: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    low_stock: bool = False,
    low_stock_threshold: int = 10,
    max_stock: int | None = None,
) -> tuple[list[Product], int]:
    conditions: list[ColumnElement[bool]] = []
    if name:
        conditions.append(Product.name.ilike(f"%{name.strip()}%"))
    if min_price is not None:
        conditions.append(Product.price >= min_price)
    if max_price is not None:
        conditions.append(Product.price <= max_price)
    if low_stock:
        conditions.append(Product.stock_quantity < low_stock_threshold)
    if max_stock is not None:
        conditions.append(Product.stock_quantity < max_stock)
    base = select(Product).where(*conditions).order_by(Product.id)
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    result = await session.scalars(base.offset((page - 1) * page_size).limit(page_size))
    return list(result), total


async def update_product(session: AsyncSession, product: Product, *, name: str, price: Decimal, stock_quantity: int) -> Product:
    product.name = name
    product.price = price
    product.stock_quantity = stock_quantity
    await session.flush()
    await session.refresh(product)
    return product


async def delete_product(session: AsyncSession, product: Product) -> None:
    await session.delete(product)
