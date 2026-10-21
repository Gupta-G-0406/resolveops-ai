from fastapi import (
    Cookie,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.session_service import get_active_session


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    session_token: str | None = Cookie(
        default=None,
        alias=settings.session_cookie_name,
    ),
) -> User:
    """Resolve the currently authenticated user."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )

    if not session_token:
        raise unauthorized

    session = await get_active_session(
        db,
        session_token,
    )

    if session is None:
        raise unauthorized

    result = await db.execute(
        select(User).where(
            User.id == session.user_id,
            User.is_active.is_(True),
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise unauthorized

    return user