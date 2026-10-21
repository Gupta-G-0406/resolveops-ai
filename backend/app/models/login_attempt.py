from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoginAttempt(Base):
    """Record a login attempt without storing raw IPs or emails."""

    __tablename__ = "login_attempts"

    __table_args__ = (
        Index(
            "ix_login_attempts_client_created",
            "client_key",
            "created_at",
        ),
        Index(
            "ix_login_attempts_account_created",
            "account_key",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    client_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    account_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    succeeded: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )