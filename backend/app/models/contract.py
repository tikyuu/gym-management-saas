from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import value_enum


class ContractStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"
    EXPIRED = "expired"
    REJECTED = "rejected"


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint(
            "starts_on <= ends_on",
            name="ck_contracts_date_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    member_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("members.id"))
    plan_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("plans.id"))
    plan_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[ContractStatus] = mapped_column(
        value_enum(ContractStatus, name="contract_status"),
        default=ContractStatus.PENDING,
        server_default=ContractStatus.PENDING.value,
    )
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class ContractStatusHistory(Base):
    __tablename__ = "contract_status_histories"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    contract_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("contracts.id"))
    executed_by_account_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user_accounts.id"),
        nullable=True,
    )
    previous_status: Mapped[ContractStatus] = mapped_column(
        value_enum(ContractStatus, name="contract_status"),
    )
    new_status: Mapped[ContractStatus] = mapped_column(
        value_enum(ContractStatus, name="contract_status"),
    )
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
