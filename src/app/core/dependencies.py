from collections.abc import AsyncIterator

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def current_user(
    token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)
) -> User:
    settings = get_settings()
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_error
    except (jwt.PyJWTError, HTTPException) as exc:
        raise credentials_error from exc
    user = await session.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if user is None:
        raise credentials_error
    return user


async def redis_connection(request: Request) -> AsyncIterator[object]:
    yield request.app.state.redis
