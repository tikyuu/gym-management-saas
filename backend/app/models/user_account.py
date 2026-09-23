from enum import StrEnum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserAccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETION_PENDING = "deletion_pending"
    ANONYMIZED = "anonymized"


class UserAccount(Base):
    __tablename__ = "user_accounts"
    __table_args__ = (
        CheckConstraint(
            "(status = 'anonymized' AND user_pool_id IS NULL AND cognito_sub IS NULL) "
            "OR (status <> 'anonymized' AND user_pool_id IS NOT NULL AND cognito_sub IS NOT NULL)",
            name="ck_user_accounts_cognito_identity",
        ),
        UniqueConstraint(
            "user_pool_id",
            "cognito_sub",
            name="uq_user_accounts_user_pool_id_cognito_sub",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_pool_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cognito_sub: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[UserAccountStatus] = mapped_column(
        Enum(
            UserAccountStatus,
            name="user_account_status",
            values_callable=lambda enum_class: [
                status.value for status in enum_class
            ],
        ),
        default=UserAccountStatus.ACTIVE,
        server_default=UserAccountStatus.ACTIVE.value,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    anonymized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
