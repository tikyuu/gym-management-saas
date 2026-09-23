from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.authorization import StaffAccess, get_staff_access, require_writable_organization
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.reservation import Reservation, ReservationStatus
from app.models.scheduling import UnavailablePeriod, UnavailablePeriodReason, WorkShift, WorkShiftStatus
from app.models.staff import Staff, StaffRole, StaffRoleStatus, StaffRoleType, StaffStatus, StaffStoreMembership, StaffStoreMembershipStatus
from app.models.store import Store


router = APIRouter()
JAPAN_TIMEZONE = ZoneInfo("Asia/Tokyo")


class ShiftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    staff_id: UUID
    store_id: UUID
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_range(self):
        validate_time_range(self.starts_at, self.ends_at)
        return self


class ShiftTimes(BaseModel):
    model_config = ConfigDict(extra="forbid")
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_range(self):
        validate_time_range(self.starts_at, self.ends_at)
        return self


class ShiftBulk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ShiftCreate] = Field(min_length=1, max_length=31)


class UnavailableCreate(ShiftTimes):
    reason: UnavailablePeriodReason


class ShiftResponse(BaseModel):
    id: UUID
    status: WorkShiftStatus
    staff_id: UUID
    store_id: UUID
    starts_at: datetime
    ends_at: datetime
    cancelled_at: datetime | None = None


class UnavailableResponse(BaseModel):
    id: UUID
    starts_at: datetime
    ends_at: datetime
    reason: UnavailablePeriodReason


def validate_time_range(starts_at: datetime, ends_at: datetime) -> None:
    if starts_at.tzinfo is None or ends_at.tzinfo is None or starts_at >= ends_at:
        raise ValueError("A timezone-aware start must precede end")


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def date_window(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    if to_date < from_date or (to_date - from_date).days > 30:
        raise HTTPException(status_code=422, detail="Date range must be at most 31 days.")
    return (
        datetime.combine(from_date, time.min, tzinfo=JAPAN_TIMEZONE).astimezone(timezone.utc),
        datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=JAPAN_TIMEZONE).astimezone(timezone.utc),
    )


def shift_response(shift: WorkShift, db_session: Session) -> ShiftResponse:
    membership = db_session.get(StaffStoreMembership, shift.staff_store_membership_id)
    return ShiftResponse(
        id=shift.id,
        status=shift.status,
        staff_id=shift.staff_id,
        store_id=membership.store_id,
        starts_at=shift.starts_at,
        ends_at=shift.ends_at,
        cancelled_at=shift.cancelled_at,
    )


def ensure_staff_can_edit(access: StaffAccess, staff_id: UUID, store_id: UUID) -> None:
    if access.organization_admin or store_id in access.managed_store_ids:
        return
    if staff_id == access.staff.id and store_id in access.trainer_store_ids:
        return
    raise HTTPException(status_code=403, detail="Shift editing is not permitted.")


def checked_shift(shift_id: UUID, access: StaffAccess, db_session: Session) -> tuple[WorkShift, StaffStoreMembership]:
    shift = db_session.get(WorkShift, shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found.")
    membership = db_session.get(StaffStoreMembership, shift.staff_store_membership_id)
    staff = db_session.get(Staff, shift.staff_id)
    if membership is None or staff is None or staff.organization_id != access.staff.organization_id:
        raise HTTPException(status_code=404, detail="Shift not found.")
    ensure_staff_can_edit(access, shift.staff_id, membership.store_id)
    return shift, membership


def ensure_no_overlap(
    staff_id: UUID, starts_at: datetime, ends_at: datetime, db_session: Session,
    exclude_shift_id: UUID | None = None,
) -> None:
    query = select(WorkShift.id).where(
        WorkShift.staff_id == staff_id,
        WorkShift.status == WorkShiftStatus.SCHEDULED,
        WorkShift.starts_at < ends_at,
        WorkShift.ends_at > starts_at,
    )
    if exclude_shift_id is not None:
        query = query.where(WorkShift.id != exclude_shift_id)
    if db_session.scalar(query.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Shift overlaps another scheduled shift.")


def ensure_reservations_within_shift(
    staff_id: UUID, previous_start: datetime, previous_end: datetime,
    starts_at: datetime, ends_at: datetime, db_session: Session,
) -> None:
    reservation = db_session.scalar(select(Reservation.id).where(
        Reservation.staff_id == staff_id,
        Reservation.status == ReservationStatus.CONFIRMED,
        Reservation.starts_at < previous_end,
        Reservation.ends_at > previous_start,
        (Reservation.starts_at < starts_at) | (Reservation.ends_at > ends_at),
    ).limit(1))
    if reservation is not None:
        raise HTTPException(status_code=409, detail="A confirmed reservation falls outside the shift.")


def create_shift_record(request: ShiftCreate, access: StaffAccess, db_session: Session) -> WorkShift:
    ensure_staff_can_edit(access, request.staff_id, request.store_id)
    if request.starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Shift must start in the future.")
    store = db_session.get(Store, request.store_id)
    staff = db_session.get(Staff, request.staff_id)
    if store is None or store.organization_id != access.staff.organization_id or staff is None or staff.organization_id != access.staff.organization_id:
        raise HTTPException(status_code=404, detail="Staff or store not found.")
    if staff.status != StaffStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Staff is inactive.")
    membership = db_session.scalar(select(StaffStoreMembership).where(
        StaffStoreMembership.staff_id == staff.id,
        StaffStoreMembership.store_id == store.id,
        StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
    ))
    if membership is None:
        raise HTTPException(status_code=409, detail="Active store membership required.")
    role = db_session.scalar(select(StaffRole.id).where(
        StaffRole.staff_id == staff.id,
        StaffRole.store_membership_id == membership.id,
        StaffRole.role == StaffRoleType.TRAINER,
        StaffRole.status == StaffRoleStatus.ACTIVE,
    ))
    if role is None:
        raise HTTPException(status_code=409, detail="Trainer role required.")
    starts_at = request.starts_at.astimezone(timezone.utc)
    ends_at = request.ends_at.astimezone(timezone.utc)
    ensure_no_overlap(staff.id, starts_at, ends_at, db_session)
    shift = WorkShift(
        staff_id=staff.id,
        staff_store_membership_id=membership.id,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    db_session.add(shift)
    db_session.flush()
    return shift


@router.get("/staff/me/work-shifts")
def list_my_shifts(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> dict:
    access = get_staff_access(current_user, db_session)
    starts_at, ends_at = date_window(from_date, to_date)
    shifts = db_session.scalars(select(WorkShift).where(
        WorkShift.staff_id == access.staff.id,
        WorkShift.starts_at < ends_at,
        WorkShift.ends_at > starts_at,
    ).order_by(WorkShift.starts_at, WorkShift.id)).all()
    return {"items": [shift_response(shift, db_session) for shift in shifts]}


@router.get("/work-shifts")
def list_management_shifts(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    store_id: UUID | None = None,
    staff_id: UUID | None = None,
) -> dict:
    access = get_staff_access(current_user, db_session)
    if not access.organization_admin and not access.managed_store_ids:
        raise HTTPException(status_code=403, detail="Manager role required.")
    if store_id is not None and not access.organization_admin and store_id not in access.managed_store_ids:
        raise HTTPException(status_code=404, detail="Store not found.")
    if staff_id is not None:
        staff = db_session.get(Staff, staff_id)
        if staff is None or staff.organization_id != access.staff.organization_id:
            raise HTTPException(status_code=404, detail="Staff not found.")
    starts_at, ends_at = date_window(from_date, to_date)
    query = select(WorkShift).join(Staff, Staff.id == WorkShift.staff_id).join(
        StaffStoreMembership,
        StaffStoreMembership.id == WorkShift.staff_store_membership_id,
    ).where(
        Staff.organization_id == access.staff.organization_id,
        WorkShift.starts_at < ends_at,
        WorkShift.ends_at > starts_at,
    )
    if not access.organization_admin:
        query = query.where(StaffStoreMembership.store_id.in_(access.managed_store_ids))
    if store_id is not None:
        query = query.where(StaffStoreMembership.store_id == store_id)
    if staff_id is not None:
        query = query.where(WorkShift.staff_id == staff_id)
    shifts = db_session.scalars(query.order_by(WorkShift.starts_at, WorkShift.id)).all()
    return {"items": [shift_response(shift, db_session) for shift in shifts]}


@router.post("/work-shifts/bulk", status_code=201)
def create_shifts_bulk(
    request: ShiftBulk,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    try:
        shifts = [create_shift_record(item, access, db_session) for item in request.items]
        response = [shift_response(shift, db_session) for shift in shifts]
        db_session.commit()
    except (IntegrityError, HTTPException) as error:
        db_session.rollback()
        if isinstance(error, IntegrityError):
            raise HTTPException(status_code=409, detail="Shift conflicts with existing data.") from error
        raise
    return {"items": response}


@router.post("/work-shifts", response_model=ShiftResponse, status_code=201)
def create_shift(
    request: ShiftCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ShiftResponse:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    try:
        shift = create_shift_record(request, access, db_session)
        response = shift_response(shift, db_session)
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="Shift overlaps another shift.") from error
    return response


@router.patch("/work-shifts/{shift_id}", response_model=ShiftResponse)
def update_shift(
    shift_id: UUID,
    request: ShiftTimes,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ShiftResponse:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    shift, _ = checked_shift(shift_id, access, db_session)
    if shift.status != WorkShiftStatus.SCHEDULED or as_utc(shift.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Shift is no longer editable.")
    starts_at = request.starts_at.astimezone(timezone.utc)
    ends_at = request.ends_at.astimezone(timezone.utc)
    if starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Shift must start in the future.")
    ensure_no_overlap(shift.staff_id, starts_at, ends_at, db_session, shift.id)
    ensure_reservations_within_shift(
        shift.staff_id, as_utc(shift.starts_at), as_utc(shift.ends_at),
        starts_at, ends_at, db_session,
    )
    shift.starts_at = starts_at
    shift.ends_at = ends_at
    try:
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="Shift overlaps another shift.") from error
    return shift_response(shift, db_session)


@router.post("/work-shifts/{shift_id}/cancel", response_model=ShiftResponse)
def cancel_shift(
    shift_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ShiftResponse:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    shift, _ = checked_shift(shift_id, access, db_session)
    if shift.status != WorkShiftStatus.SCHEDULED or as_utc(shift.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Shift is no longer cancellable.")
    reservation = db_session.scalar(select(Reservation.id).where(
        Reservation.staff_id == shift.staff_id,
        Reservation.status == ReservationStatus.CONFIRMED,
        Reservation.starts_at < shift.ends_at,
        Reservation.ends_at > shift.starts_at,
    ).limit(1))
    if reservation is not None:
        raise HTTPException(status_code=409, detail="Confirmed reservations must be resolved first.")
    shift.status = WorkShiftStatus.CANCELLED
    shift.cancelled_at = datetime.now(timezone.utc)
    db_session.commit()
    return shift_response(shift, db_session)


def checked_unavailable(shift_id: UUID, unavailable_period_id: UUID, access: StaffAccess, db_session: Session) -> tuple[WorkShift, UnavailablePeriod]:
    shift, _ = checked_shift(shift_id, access, db_session)
    period = db_session.get(UnavailablePeriod, unavailable_period_id)
    if period is None or period.work_shift_id != shift.id:
        raise HTTPException(status_code=404, detail="Unavailable period not found.")
    return shift, period


def validate_unavailable(shift: WorkShift, starts_at: datetime, ends_at: datetime, db_session: Session, exclude_id: UUID | None = None) -> None:
    if shift.status != WorkShiftStatus.SCHEDULED:
        raise HTTPException(status_code=409, detail="Shift is not scheduled.")
    if starts_at < as_utc(shift.starts_at) or ends_at > as_utc(shift.ends_at):
        raise HTTPException(status_code=422, detail="Unavailable period must fit within shift.")
    if starts_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="Unavailable period must be in the future.")
    query = select(UnavailablePeriod.id).where(
        UnavailablePeriod.work_shift_id == shift.id,
        UnavailablePeriod.starts_at < ends_at,
        UnavailablePeriod.ends_at > starts_at,
    )
    if exclude_id is not None:
        query = query.where(UnavailablePeriod.id != exclude_id)
    if db_session.scalar(query.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Unavailable periods overlap.")
    reservation = db_session.scalar(select(Reservation.id).where(
        Reservation.staff_id == shift.staff_id,
        Reservation.status == ReservationStatus.CONFIRMED,
        Reservation.starts_at < ends_at,
        Reservation.ends_at > starts_at,
    ).limit(1))
    if reservation is not None:
        raise HTTPException(status_code=409, detail="Unavailable period overlaps a reservation.")


@router.post("/work-shifts/{shift_id}/unavailable-periods", response_model=UnavailableResponse, status_code=201)
def create_unavailable(
    shift_id: UUID,
    request: UnavailableCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> UnavailableResponse:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    shift, _ = checked_shift(shift_id, access, db_session)
    starts_at = request.starts_at.astimezone(timezone.utc)
    ends_at = request.ends_at.astimezone(timezone.utc)
    validate_unavailable(shift, starts_at, ends_at, db_session)
    period = UnavailablePeriod(work_shift_id=shift.id, starts_at=starts_at, ends_at=ends_at, reason=request.reason)
    db_session.add(period)
    try:
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="Unavailable periods overlap.") from error
    db_session.refresh(period)
    return UnavailableResponse.model_validate(period, from_attributes=True)


@router.patch("/work-shifts/{shift_id}/unavailable-periods/{unavailable_period_id}", response_model=UnavailableResponse)
def update_unavailable(
    shift_id: UUID,
    unavailable_period_id: UUID,
    request: UnavailableCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> UnavailableResponse:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    shift, period = checked_unavailable(shift_id, unavailable_period_id, access, db_session)
    if as_utc(period.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Unavailable period is no longer editable.")
    starts_at = request.starts_at.astimezone(timezone.utc)
    ends_at = request.ends_at.astimezone(timezone.utc)
    validate_unavailable(shift, starts_at, ends_at, db_session, period.id)
    period.starts_at = starts_at
    period.ends_at = ends_at
    period.reason = request.reason
    try:
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="Unavailable periods overlap.") from error
    return UnavailableResponse.model_validate(period, from_attributes=True)


@router.delete("/work-shifts/{shift_id}/unavailable-periods/{unavailable_period_id}", status_code=204)
def delete_unavailable(
    shift_id: UUID,
    unavailable_period_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> None:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    shift, period = checked_unavailable(shift_id, unavailable_period_id, access, db_session)
    if shift.status != WorkShiftStatus.SCHEDULED or as_utc(period.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Unavailable period is no longer removable.")
    db_session.delete(period)
    db_session.commit()
