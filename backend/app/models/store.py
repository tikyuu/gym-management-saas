from datetime import date, datetime, time
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StoreStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class Store(Base):
    __tablename__ = "stores"
    __table_args__ = (
        CheckConstraint(
            "booking_interval_minutes IN (10, 15, 30)",
            name="ck_stores_booking_interval_minutes",
        ),
        CheckConstraint(
            "free_cancellation_hours BETWEEN 0 AND 168",
            name="ck_stores_free_cancellation_hours",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id"),
    )
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(Text)
    phone_number: Mapped[str] = mapped_column(String(32))
    status: Mapped[StoreStatus] = mapped_column(
        Enum(StoreStatus, name="store_status"),
        default=StoreStatus.DRAFT,
        server_default=StoreStatus.DRAFT.value,
    )
    booking_interval_minutes: Mapped[int] = mapped_column(
        SmallInteger,
        default=30,
        server_default="30",
    )
    free_cancellation_hours: Mapped[int] = mapped_column(
        SmallInteger,
        default=24,
        server_default="24",
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


class StoreRegularHour(Base):
    __tablename__ = "store_regular_hours"
    __table_args__ = (
        CheckConstraint(
            "day_of_week BETWEEN 1 AND 7",
            name="ck_store_regular_hours_day_of_week",
        ),
        CheckConstraint(
            "opens_at < closes_at",
            name="ck_store_regular_hours_time_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("stores.id"))
    day_of_week: Mapped[int] = mapped_column(SmallInteger)
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class StoreSpecialDay(Base):
    __tablename__ = "store_special_days"
    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "business_date",
            name="uq_store_special_days_store_id_business_date",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("stores.id"))
    business_date: Mapped[date] = mapped_column(Date)
    is_closed: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class StoreSpecialDayHour(Base):
    __tablename__ = "store_special_day_hours"
    __table_args__ = (
        CheckConstraint(
            "opens_at < closes_at",
            name="ck_store_special_day_hours_time_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    special_day_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("store_special_days.id"),
    )
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
