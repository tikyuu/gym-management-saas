from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.v1.booking_catalog import PlanSnapshot
from app.api.v1.members import get_member_profile
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.catalog import AvailabilityStatus, Menu, MenuStatus, StoreMenu, TrainerMenu
from app.models.contract import Contract, ContractStatus
from app.models.member import MemberStatus
from app.models.organization import OrganizationStatus
from app.models.reservation import Reservation, ReservationStatus
from app.models.scheduling import UnavailablePeriod, WorkShift, WorkShiftStatus
from app.models.staff import (
    Staff,
    StaffRole,
    StaffRoleStatus,
    StaffRoleType,
    StaffStatus,
    StaffStoreMembership,
    StaffStoreMembershipStatus,
)
from app.models.store import (
    Store,
    StoreRegularHour,
    StoreSpecialDay,
    StoreSpecialDayHour,
    StoreStatus,
)


router = APIRouter()
JAPAN_TIMEZONE = ZoneInfo("Asia/Tokyo")


class AvailableSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime


class AvailabilityResponse(BaseModel):
    date: date
    slots: list[AvailableSlot]


def as_japan_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(JAPAN_TIMEZONE)


def overlaps(
    starts_at: datetime,
    ends_at: datetime,
    other_starts_at: datetime,
    other_ends_at: datetime,
) -> bool:
    return starts_at < as_japan_time(other_ends_at) and as_japan_time(other_starts_at) < ends_at


def available_slots(
    business_hours: list[tuple[time, time]],
    booking_interval_minutes: int,
    duration_minutes: int,
    target_date: date,
    shifts: list[WorkShift],
    unavailable_periods: list[UnavailablePeriod],
    reservations: list[Reservation],
    member_id: UUID,
    now: datetime,
) -> list[AvailableSlot]:
    slots: list[AvailableSlot] = []
    seen_starts: set[datetime] = set()
    interval = timedelta(minutes=booking_interval_minutes)
    duration = timedelta(minutes=duration_minutes)

    for opens_at, closes_at in business_hours:
        starts_at = datetime.combine(target_date, opens_at, JAPAN_TIMEZONE)
        closing = datetime.combine(target_date, closes_at, JAPAN_TIMEZONE)
        while starts_at + duration <= closing:
            ends_at = starts_at + duration
            if starts_at > now and starts_at not in seen_starts and not any(
                reservation.member_id == member_id
                and overlaps(starts_at, ends_at, reservation.starts_at, reservation.ends_at)
                for reservation in reservations
            ):
                for shift in shifts:
                    if (
                        as_japan_time(shift.starts_at) <= starts_at
                        and ends_at <= as_japan_time(shift.ends_at)
                        and not any(
                            period.work_shift_id == shift.id
                            and overlaps(starts_at, ends_at, period.starts_at, period.ends_at)
                            for period in unavailable_periods
                        )
                        and not any(
                            reservation.staff_id == shift.staff_id
                            and overlaps(
                                starts_at,
                                ends_at,
                                reservation.starts_at,
                                reservation.ends_at,
                            )
                            for reservation in reservations
                        )
                    ):
                        slots.append(AvailableSlot(starts_at=starts_at, ends_at=ends_at))
                        seen_starts.add(starts_at)
                        break
            starts_at += interval

    return sorted(slots, key=lambda slot: slot.starts_at)


@router.get("/stores/{store_id}/availability", response_model=AvailabilityResponse)
def get_availability(
    store_id: UUID,
    target_date: Annotated[date, Query(alias="date")],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    menu_id: UUID,
    trainer_id: UUID | None = None,
) -> AvailabilityResponse:
    member, organization = get_member_profile(current_user, db_session)
    if member.status != MemberStatus.ACTIVE or organization.status != OrganizationStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking is unavailable.")

    store = db_session.scalar(
        select(Store).where(
            Store.id == store_id,
            Store.organization_id == organization.id,
            Store.status == StoreStatus.ACTIVE,
        )
    )
    menu = db_session.scalar(
        select(Menu)
        .join(StoreMenu, StoreMenu.menu_id == Menu.id)
        .where(
            Menu.id == menu_id,
            Menu.organization_id == organization.id,
            Menu.status == MenuStatus.ACTIVE,
            StoreMenu.store_id == store_id,
            StoreMenu.status == AvailabilityStatus.ACTIVE,
        )
    )
    if store is None or menu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking is unavailable.")

    contract_snapshots = db_session.scalars(
        select(Contract.plan_snapshot).where(
            Contract.member_id == member.id,
            Contract.status.in_((ContractStatus.ACTIVE, ContractStatus.SCHEDULED)),
            Contract.starts_on <= target_date,
            Contract.ends_on >= target_date,
        )
    ).all()
    if not any(
        store_id in snapshot.store_ids and menu_id in snapshot.menu_ids
        for snapshot in (PlanSnapshot.model_validate(value) for value in contract_snapshots)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking is unavailable.")

    trainer_query = (
        select(StaffStoreMembership.id)
        .join(Staff, Staff.id == StaffStoreMembership.staff_id)
        .join(StaffRole, StaffRole.store_membership_id == StaffStoreMembership.id)
        .join(TrainerMenu, TrainerMenu.staff_store_membership_id == StaffStoreMembership.id)
        .where(
            StaffStoreMembership.store_id == store_id,
            StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
            Staff.organization_id == organization.id,
            Staff.status == StaffStatus.ACTIVE,
            StaffRole.staff_id == Staff.id,
            StaffRole.role == StaffRoleType.TRAINER,
            StaffRole.status == StaffRoleStatus.ACTIVE,
            TrainerMenu.menu_id == menu_id,
            TrainerMenu.status == AvailabilityStatus.ACTIVE,
        )
    )
    if trainer_id is not None:
        trainer_query = trainer_query.where(Staff.id == trainer_id)
    membership_ids = db_session.scalars(trainer_query).all()
    if trainer_id is not None and not membership_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trainer is unavailable.")
    if not membership_ids:
        return AvailabilityResponse(date=target_date, slots=[])

    special_day = db_session.scalar(
        select(StoreSpecialDay).where(
            StoreSpecialDay.store_id == store_id,
            StoreSpecialDay.business_date == target_date,
        )
    )
    if special_day is not None:
        if special_day.is_closed:
            return AvailabilityResponse(date=target_date, slots=[])
        business_hours = db_session.execute(
            select(StoreSpecialDayHour.opens_at, StoreSpecialDayHour.closes_at).where(
                StoreSpecialDayHour.special_day_id == special_day.id
            )
        ).all()
    else:
        business_hours = db_session.execute(
            select(StoreRegularHour.opens_at, StoreRegularHour.closes_at).where(
                StoreRegularHour.store_id == store_id,
                StoreRegularHour.day_of_week == target_date.isoweekday(),
            )
        ).all()
    if not business_hours:
        return AvailabilityResponse(date=target_date, slots=[])

    day_start = datetime.combine(target_date, time.min, JAPAN_TIMEZONE).astimezone(timezone.utc)
    day_end = (
        datetime.combine(target_date, time.min, JAPAN_TIMEZONE) + timedelta(days=1)
    ).astimezone(timezone.utc)
    shifts = db_session.scalars(
        select(WorkShift).where(
            WorkShift.staff_store_membership_id.in_(membership_ids),
            WorkShift.status == WorkShiftStatus.SCHEDULED,
            WorkShift.starts_at < day_end,
            WorkShift.ends_at > day_start,
        )
    ).all()
    if not shifts:
        return AvailabilityResponse(date=target_date, slots=[])

    unavailable_periods = db_session.scalars(
        select(UnavailablePeriod).where(
            UnavailablePeriod.work_shift_id.in_([shift.id for shift in shifts])
        )
    ).all()
    reservations = db_session.scalars(
        select(Reservation).where(
            Reservation.status == ReservationStatus.CONFIRMED,
            or_(
                Reservation.member_id == member.id,
                Reservation.staff_id.in_([shift.staff_id for shift in shifts]),
            ),
            Reservation.starts_at < day_end,
            Reservation.ends_at > day_start,
        )
    ).all()

    return AvailabilityResponse(
        date=target_date,
        slots=available_slots(
            business_hours=list(business_hours),
            booking_interval_minutes=store.booking_interval_minutes,
            duration_minutes=menu.duration_minutes,
            target_date=target_date,
            shifts=shifts,
            unavailable_periods=unavailable_periods,
            reservations=reservations,
            member_id=member.id,
            now=datetime.now(JAPAN_TIMEZONE),
        ),
    )
