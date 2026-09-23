from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import value_enum


class WorkShiftStatus(StrEnum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class UnavailablePeriodReason(StrEnum):
    BREAK = "break"
    OTHER = "other"


class WorkShift(Base):
    __tablename__ = "work_shifts"
    __table_args__ = (
        CheckConstraint(
            "starts_at < ends_at",
            name="ck_work_shifts_time_range",
        ),
        CheckConstraint(
            "(status = 'scheduled' AND cancelled_at IS NULL) "
            "OR (status = 'cancelled' AND cancelled_at IS NOT NULL)",
            name="ck_work_shifts_cancelled_at",
        ),
        ForeignKeyConstraint(
            ["staff_store_membership_id", "staff_id"],
            ["staff_store_memberships.id", "staff_store_memberships.staff_id"],
            name="fk_work_shifts_membership_staff",
        ),
        ExcludeConstraint(
            ("staff_id", "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=text("status = 'scheduled'"),
            name="ex_work_shifts_staff_scheduled_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    staff_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("staff.id"))
    staff_store_membership_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("staff_store_memberships.id"),
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[WorkShiftStatus] = mapped_column(
        value_enum(WorkShiftStatus, name="work_shift_status"),
        default=WorkShiftStatus.SCHEDULED,
        server_default=WorkShiftStatus.SCHEDULED.value,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
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


class UnavailablePeriod(Base):
    __tablename__ = "unavailable_periods"
    __table_args__ = (
        CheckConstraint(
            "starts_at < ends_at",
            name="ck_unavailable_periods_time_range",
        ),
        ExcludeConstraint(
            ("work_shift_id", "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            name="ex_unavailable_periods_work_shift_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    work_shift_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("work_shifts.id"),
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[UnavailablePeriodReason] = mapped_column(
        value_enum(UnavailablePeriodReason, name="unavailable_period_reason"),
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
