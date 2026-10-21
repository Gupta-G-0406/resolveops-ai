from types import SimpleNamespace

from app.models.user import UserRole


def make_test_user(
    role: UserRole = UserRole.ADMIN,
):
    """Create a lightweight user for isolated API tests."""

    return SimpleNamespace(
        id=1,
        email="rbac-test@example.com",
        full_name="RBAC Test User",
        role=role.value,
        is_active=True,
    )


async def override_current_user():
    """Return an authenticated admin for mocked API tests."""

    return make_test_user()