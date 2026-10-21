import hashlib
import hmac
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.login_attempt import LoginAttempt


class LoginRateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("Too many login attempts")


def make_identifier(value: str, namespace: str) -> str:
    """Create a privacy-preserving keyed identifier."""

    message = f"{namespace}:{value}".encode("utf-8")

    return hmac.new(
        settings.login_rate_limit_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def get_login_keys(
    *,
    client_ip: str,
    email: str,
) -> tuple[str, str]:
    """Derive identifiers without storing raw IP or email."""

    client_key = make_identifier(
        client_ip,
        "client",
    )

    account_key = make_identifier(
        email.strip().lower(),
        "account",
    )

    return client_key, account_key


async def lock_login_keys(
    db: AsyncSession,
    *,
    client_key: str,
    account_key: str,
) -> None:
    """
    Serialize rate-limit checks for overlapping clients/accounts.

    Locks are held until the current transaction ends.
    """

    lock_names = sorted([
        f"login-client:{client_key}",
        f"login-account:{account_key}",
    ])

    for lock_name in lock_names:
        await db.execute(
            text(
                "SELECT pg_advisory_xact_lock("
                "hashtextextended(:lock_name, 0)"
                ")"
            ),
            {"lock_name": lock_name},
        )


async def check_login_rate_limit(
    db: AsyncSession,
    *,
    client_key: str,
    account_key: str,
) -> None:
    """Check both limits within the current transaction."""

    now = datetime.now(timezone.utc)

    window_start = now - timedelta(
        minutes=settings.login_rate_limit_window_minutes
    )

    client_result = await db.execute(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.client_key == client_key,
            LoginAttempt.created_at >= window_start,
        )
    )

    client_count = client_result.scalar_one()

    account_result = await db.execute(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.account_key == account_key,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.created_at >= window_start,
        )
    )

    account_failures = account_result.scalar_one()

    if (
        client_count >= settings.login_rate_limit_client_max
        or account_failures >= settings.login_rate_limit_account_max
    ):
        retry_after = (
            settings.login_rate_limit_window_minutes * 60
        )

        raise LoginRateLimitExceeded(
            retry_after=retry_after
        )


async def record_login_attempt(
    db: AsyncSession,
    *,
    client_key: str,
    account_key: str,
    succeeded: bool,
) -> None:
    """Record an authentication result."""

    db.add(
        LoginAttempt(
            client_key=client_key,
            account_key=account_key,
            succeeded=succeeded,
        )
    )

    await db.flush()