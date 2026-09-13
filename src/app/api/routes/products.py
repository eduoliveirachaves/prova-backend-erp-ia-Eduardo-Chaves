from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_json, invalidate, product_key, set_json
from app.core.config import get_settings
from app.core.dependencies import current_user
from app.db.session import get_session
from app.models import User
from app.repositories.product_repository import list_products
from app.schemas.product import ProductCreate, ProductList, ProductRead, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/api/v1/products", tags=["products"])


async def enqueue_alert(request: Request, product_id: int, quantity: int) -> None:
    if quantity < get_settings().low_stock_threshold:
        try:
            await request.app.state.arq.enqueue_job("process_low_stock_alert", product_id, quantity)
        except Exception:
            request.app.state.logger.warning("alert_enqueue_failed", extra={"product_id": product_id}, exc_info=True)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(current_user),
) -> ProductRead:
    product = await product_service.create(session, **payload.model_dump())
    await session.commit()
    await session.refresh(product)
    await invalidate(request.app.state.redis, product_key(product.id))
    await enqueue_alert(request, product.id, product.stock_quantity)
    return ProductRead.model_validate(product)


@router.get("", response_model=ProductList)
async def list_product_items(
    page: int = 1,
    page_size: int = 20,
    name: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    low_stock: bool = False,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(current_user),
) -> ProductList:
    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(status_code=422, detail="page must be >= 1 and page_size must be between 1 and 100")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=422, detail="min_price cannot exceed max_price")
    products, total = await list_products(
        session,
        page=page,
        page_size=page_size,
        name=name,
        min_price=min_price,
        max_price=max_price,
        low_stock=low_stock,
        low_stock_threshold=get_settings().low_stock_threshold,
    )
    return ProductList(items=[ProductRead.model_validate(item) for item in products], total=total, page=page, page_size=page_size)


@router.get("/{product_id}", response_model=ProductRead)
async def read_product(
    product_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(current_user),
) -> ProductRead:
    key = product_key(product_id)
    cached = await get_json(request.app.state.redis, key)
    if cached is not None:
        return ProductRead.model_validate(cached)
    try:
        product = await product_service.get(session, product_id)
    except product_service.ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail="product not found") from exc
    result = ProductRead.model_validate(product)
    await set_json(request.app.state.redis, key, result.model_dump(mode="json"), get_settings().cache_ttl_seconds)
    return result


@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(current_user),
) -> ProductRead:
    try:
        product = await product_service.update(session, product_id, **payload.model_dump())
    except product_service.ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail="product not found") from exc
    await session.commit()
    await session.refresh(product)
    await invalidate(request.app.state.redis, product_key(product_id))
    await enqueue_alert(request, product.id, product.stock_quantity)
    return ProductRead.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(current_user),
) -> Response:
    try:
        await product_service.remove(session, product_id)
    except product_service.ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail="product not found") from exc
    await session.commit()
    await invalidate(request.app.state.redis, product_key(product_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
