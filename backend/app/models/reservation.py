from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReservationStatus(StrEnum):
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class UsageEntryType(StrEnum):
    GRANT = "grant"
    CARRYOVER = "carryover"
    HOLD = "hold"
    RELEASE = "release"
    CONSUME = "consume"
    EXPIRE = "expire"
    ADJUSTMENT = "adjustment"


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "starts_at < ends_at",
            name="ck_reservations_time_range",
        ),
        ForeignKeyConstraint(
            ["staff_store_membership_id", "staff_id"],
            ["staff_store_memberships.id", "staff_store_memberships.staff_id"],
            name="fk_reservations_membership_staff",
        ),
        ExcludeConstraint(
            ("member_id", "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=text("status = 'confirmed'"),
            name="ex_reservations_member_confirmed_time",
        ),
        ExcludeConstraint(
            ("staff_id", "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=text("status = 'confirmed'"),
            name="ex_reservations_staff_confirmed_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    member_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("members.id"))
    contract_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("contracts.id"))
    store_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("stores.id"))
    staff_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("staff.id"))
    staff_store_membership_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("staff_store_memberships.id"),
    )
    menu_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("menus.id"))
    reservation_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"),
        default=ReservationStatus.CONFIRMED,
        server_default=ReservationStatus.CONFIRMED.value,
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


class ReservationStatusHistory(Base):
    __tablename__ = "reservation_status_histories"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    reservation_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("reservations.id"),
    )
    executed_by_account_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user_accounts.id"),
        nullable=True,
    )
    previous_status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"),
    )
    new_status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="reservation_status"),
    )
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class UsageEntry(Base):
    __tablename__ = "usage_entries"
    __table_args__ = (
        CheckConstraint(
            "usage_period_starts_on <= usage_period_ends_on",
            name="ck_usage_entries_period_range",
        ),
        CheckConstraint(
            "entry_type <> 'adjustment' "
            "OR (reason IS NOT NULL AND executed_by_account_id IS NOT NULL)",
            name="ck_usage_entries_adjustment_context",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    contract_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("contracts.id"))
    reservation_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("reservations.id"),
        nullable=True,
    )
    executed_by_account_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user_accounts.id"),
        nullable=True,
    )
    entry_type: Mapped[UsageEntryType] = mapped_column(
        Enum(UsageEntryType, name="usage_entry_type"),
    )
    available_usage_delta: Mapped[int] = mapped_column(Integer)
    reserved_usage_delta: Mapped[int] = mapped_column(Integer)
    consumed_usage_delta: Mapped[int] = mapped_column(Integer)
    usage_period_starts_on: Mapped[date] = mapped_column(Date)
    usage_period_ends_on: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
