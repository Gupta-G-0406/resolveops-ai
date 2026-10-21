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
    """Enforce rolling-window login limits with accurate Retry-After."""

    now = datetime.now(timezone.utc)

    window = timedelta(
        minutes=settings.login_rate_limit_window_minutes
    )

    window_start = now - window

    # Get timestamps for client attempts in the active window.
    client_result = await db.execute(
        select(LoginAttempt.created_at)
        .where(
            LoginAttempt.client_key == client_key,
            LoginAttempt.created_at > window_start,
        )
        .order_by(LoginAttempt.created_at.asc())
    )

    client_attempts = client_result.scalars().all()

    # Find the most recent successful login for this account.
    last_success_result = await db.execute(
        select(func.max(LoginAttempt.created_at))
        .where(
            LoginAttempt.account_key == account_key,
            LoginAttempt.succeeded.is_(True),
        )
    )

    last_success_at = last_success_result.scalar_one_or_none()

    # Only failures after the latest success count toward lockout.
    account_window_start = window_start

    if last_success_at is not None:
        account_window_start = max(
            window_start,
            last_success_at,
        )
    # Get timestamps for failed account attempts.
    account_result = await db.execute(
        select(LoginAttempt.created_at)
        .where(
            LoginAttempt.account_key == account_key,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.created_at > account_window_start,
        )
        .order_by(LoginAttempt.created_at.asc())
    )

    account_failures = account_result.scalars().all()

    retry_after_values = []

    if len(client_attempts) >= settings.login_rate_limit_client_max:
        # The request becomes allowed once enough old attempts expire.
        threshold_index = (
            len(client_attempts)
            - settings.login_rate_limit_client_max
        )

        expiry = client_attempts[threshold_index] + window

        retry_after_values.append(
            max(1, math.ceil((expiry - now).total_seconds()))
        )

    if len(account_failures) >= settings.login_rate_limit_account_max:
        threshold_index = (
            len(account_failures)
            - settings.login_rate_limit_account_max
        )

        expiry = account_failures[threshold_index] + window

        retry_after_values.append(
            max(1, math.ceil((expiry - now).total_seconds()))
        )

    if retry_after_values:
        raise LoginRateLimitExceeded(
            retry_after=max(retry_after_values)
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