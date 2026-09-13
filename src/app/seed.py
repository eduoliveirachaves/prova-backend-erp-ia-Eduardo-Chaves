import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models import User


async def seed_demo_user() -> None:
    settings = get_settings()
    async with SessionFactory() as session:
        user = await session.scalar(select(User).where(User.username == settings.demo_username))
        if user is None:
            session.add(
                User(
                    username=settings.demo_username,
                    password_hash=hash_password(settings.demo_password),
                    is_active=True,
                )
            )
            await session.commit()


def main() -> None:
    asyncio.run(seed_demo_user())


if __name__ == "__main__":
    main()
