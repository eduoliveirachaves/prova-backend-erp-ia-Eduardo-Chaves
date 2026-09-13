from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product
from app.schemas.agent import StockQueryArguments, ToolCall
from app.services import product_service

ToolHandler = Callable[[AsyncSession, StockQueryArguments], Awaitable[list[Product]]]


class UnsupportedToolError(ValueError):
    pass


async def find_low_stock(session: AsyncSession, arguments: StockQueryArguments) -> list[Product]:
    return await product_service.list_low_stock(
        session,
        max_quantity=arguments.max_quantity,
    )


TOOL_HANDLERS: dict[str, ToolHandler] = {"find_low_stock": find_low_stock}


async def execute_tool_call(session: AsyncSession, call: ToolCall) -> list[Product]:
    handler = TOOL_HANDLERS.get(call.name)
    if handler is None:
        raise UnsupportedToolError(call.name)
    return await handler(session, call.arguments)
