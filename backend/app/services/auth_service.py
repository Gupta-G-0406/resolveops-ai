from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    hash_password,
    verify_password,
)
from app.models.user import User


# Used when an email address does not exist.
# Prevents skipping expensive password verification.
DUMMY_PASSWORD_HASH = hash_password(
    "resolveops-dummy-password-not-for-login"
)


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    """Find a user by normalized email."""

    normalized_email = email.strip().lower()

    result = await db.execute(
        select(User).where(
            User.email == normalized_email
        )
    )

    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> User | None:
    """Authenticate credentials without skipping password verification."""

    user = await get_user_by_email(db, email)

    # Even unknown accounts perform an Argon2 verification.
    stored_hash = (
        user.password_hash
        if user is not None
        else DUMMY_PASSWORD_HASH
    )

    password_valid = verify_password(
        password,
        stored_hash,
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    if not password_valid:
        return None

    return user