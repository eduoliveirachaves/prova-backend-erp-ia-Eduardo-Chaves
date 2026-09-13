from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_user(session: AsyncSession, username: str) -> User | None:
    return await session.scalar(select(User).where(User.username == username))
