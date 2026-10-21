from datetime import timedelta

from app.services.login_rate_limit_service import (
    LoginRateLimitExceeded,
    get_login_keys,
    lock_login_keys,
    check_login_rate_limit,
    record_login_attempt,
)
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    AuthUserResponse,
    AuthMessageResponse,
)
from app.services.auth_service import authenticate_user
from app.services.session_service import (
    create_session,
    revoke_session,
    revoke_all_user_sessions,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)

# Development frontend origin.
# Keep this aligned with the frontend origin in CORS settings.
ALLOWED_ORIGINS = set(settings.auth_allowed_origins)

def require_trusted_origin(request: Request) -> None:
    """Reject unsafe cross-origin authentication requests."""

    origin = request.headers.get("origin")

    if origin not in ALLOWED_ORIGINS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Untrusted request origin",
        )


@router.post("/login", response_model=AuthUserResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    require_trusted_origin(request)

    # Client IP is taken from the direct connection.
    # Do not blindly trust X-Forwarded-For.
    client_ip = (
        request.client.host
        if request.client is not None
        else "unknown"
    )

    client_key, account_key = get_login_keys(
        client_ip=client_ip,
        email=payload.email,
    )

    # Both locks remain held until transaction commit/rollback.
    await lock_login_keys(
        db,
        client_key=client_key,
        account_key=account_key,
    )

    try:
        await check_login_rate_limit(
            db,
            client_key=client_key,
            account_key=account_key,
        )
    except LoginRateLimitExceeded as exc:
        await db.rollback()

        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={
                "Retry-After": str(exc.retry_after),
            },
        ) from exc

    user = await authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
    )

    await record_login_attempt(
        db,
        client_key=client_key,
        account_key=account_key,
        succeeded=user is not None,
    )

    if user is None:
        # Persist failed attempts before returning 401.
        await db.commit()

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = await create_session(
        db,
        user_id=user.id,
        lifetime_hours=settings.session_lifetime_hours,
    )

    await db.commit()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_lifetime_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )

    return user


@router.get(
    "/me",
    response_model=AuthUserResponse,
)
async def get_me(
    user: User = Depends(get_current_user),
):
    return user


@router.post(
    "/logout",
    response_model=AuthMessageResponse,
)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    require_trusted_origin(request)

    token = request.cookies.get(
        settings.session_cookie_name
    )

    if token:
        await revoke_session(db, token)
        await db.commit()

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )

    return {"message": "Logged out successfully"}


@router.post(
    "/logout-all",
    response_model=AuthMessageResponse,
)
async def logout_all(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    require_trusted_origin(request)

    await revoke_all_user_sessions(
        db,
        user_id=user.id,
    )

    await db.commit()

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )

    return {"message": "All sessions revoked"}