from enum import StrEnum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import value_enum


class OrganizationStatus(StrEnum):
    PREPARING = "preparing"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[OrganizationStatus] = mapped_column(
        value_enum(OrganizationStatus, name="organization_status"),
        default=OrganizationStatus.PREPARING,
        server_default=OrganizationStatus.PREPARING.value,
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


class OrganizationStatusHistory(Base):
    __tablename__ = "organization_status_histories"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id"),
    )
    executed_by_account_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user_accounts.id"),
        nullable=True,
    )
    previous_status: Mapped[OrganizationStatus] = mapped_column(
        value_enum(OrganizationStatus, name="organization_status"),
    )
    new_status: Mapped[OrganizationStatus] = mapped_column(
        value_enum(OrganizationStatus, name="organization_status"),
    )
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
