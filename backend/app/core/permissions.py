from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.models.user import User, UserRole


def require_roles(
    *allowed_roles: UserRole,
) -> Callable:
    """Require the authenticated user to have an allowed role."""

    async def role_checker(
        user: User = Depends(get_current_user),
    ) -> User:

        if user.role not in {
            role.value for role in allowed_roles
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return role_checker