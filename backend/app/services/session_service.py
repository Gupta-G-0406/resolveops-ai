import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_session import UserSession


SESSION_TOKEN_BYTES = 32


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """Hash a session token before storing it."""
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


async def create_session(
    db: AsyncSession,
    *,
    user_id: int,
    lifetime_hours: int = 24,
) -> str:
    """Create a session and return its raw token."""

    if lifetime_hours <= 0:
        raise ValueError(
            "Session lifetime must be positive"
        )

    raw_token = generate_session_token()

    now = datetime.now(timezone.utc)

    session = UserSession(
        user_id=user_id,
        token_hash=hash_session_token(raw_token),
        created_at=now,
        expires_at=now + timedelta(hours=lifetime_hours),
    )

    db.add(session)
    await db.flush()

    return raw_token


async def get_active_session(
    db: AsyncSession,
    token: str,
) -> UserSession | None:
    """Find a session that is neither expired nor revoked."""

    if not token:
        return None

    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(UserSession).where(
            UserSession.token_hash == hash_session_token(token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )

    return result.scalar_one_or_none()


async def revoke_session(
    db: AsyncSession,
    token: str,
) -> None:
    """Revoke one session."""

    if not token:
        return

    await db.execute(
        update(UserSession)
        .where(
            UserSession.token_hash == hash_session_token(token),
            UserSession.revoked_at.is_(None),
        )
        .values(
            revoked_at=datetime.now(timezone.utc)
        )
    )



async def revoke_all_user_sessions(
    db: AsyncSession,
    user_id: int,
) -> None:
    """Revoke every non-revoked session belonging to a user."""

    await db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.revoked_at.is_(None),
        )
        .values(
            revoked_at=datetime.now(timezone.utc)
        )
    )
