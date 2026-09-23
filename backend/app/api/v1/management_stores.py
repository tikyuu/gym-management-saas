from datetime import date, datetime, time, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.v1.authorization import get_staff_access, require_writable_organization
from app.api.v1.pagination import Page, page
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.contract import Contract, ContractStatus
from app.models.reservation import Reservation, ReservationStatus
from app.models.store import (
    Store,
    StoreRegularHour,
    StoreSpecialDay,
    StoreSpecialDayHour,
    StoreStatus,
)


router = APIRouter()


class StorePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1)
    phone_number: str = Field(min_length=1, max_length=32)


class StorePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1)
    phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    booking_interval_minutes: int | None = None
    free_cancellation_hours: int | None = Field(default=None, ge=0, le=168)

    @model_validator(mode="after")
    def validate_interval(self):
        if self.booking_interval_minutes is not None and self.booking_interval_minutes not in (10, 15, 30):
            raise ValueError("booking_interval_minutes must be 10, 15, or 30")
        return self


class StatusPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: StoreStatus
    reason: str = Field(min_length=1, max_length=1000)


class Hour(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opens_at: time
    closes_at: time

    @model_validator(mode="after")
    def validate_range(self):
        if self.opens_at >= self.closes_at:
            raise ValueError("opens_at must precede closes_at")
        return self


class RegularHour(Hour):
    day_of_week: int = Field(ge=1, le=7)


class RegularHoursPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: list[RegularHour]


class SpecialDayPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_closed: bool
    reason: str | None = None
    hours: list[Hour]

    @model_validator(mode="after")
    def validate_closed(self):
        if self.is_closed and self.hours:
            raise ValueError("Closed days must not contain hours")
        return self


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    address: str
    phone_number: str
    status: StoreStatus
    booking_interval_minutes: int
    free_cancellation_hours: int


def store_for_access(store_id: UUID, access, db_session: Session) -> Store:
    store = db_session.get(Store, store_id)
    if store is None or store.organization_id != access.staff.organization_id:
        raise HTTPException(status_code=404, detail="Store not found.")
    access.require_store_manager(store.id)
    return store


def has_future_reservations(store_id: UUID, db_session: Session) -> bool:
    return db_session.scalar(
        select(Reservation.id).where(
            Reservation.store_id == store_id,
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.starts_at > datetime.now(timezone.utc),
        ).limit(1)
    ) is not None


def ensure_no_future_reservations(store_id: UUID, db_session: Session) -> None:
    if has_future_reservations(store_id, db_session):
        raise HTTPException(status_code=409, detail="Future reservations must be resolved first.")


def ensure_disjoint(hours: list[Hour]) -> None:
    ordered = sorted(hours, key=lambda value: value.opens_at)
    if any(first.closes_at > second.opens_at for first, second in zip(ordered, ordered[1:])):
        raise HTTPException(status_code=422, detail="Opening hours overlap.")


@router.get("/management/stores", response_model=Page[StoreResponse])
def list_management_stores(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    status: StoreStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> Page[StoreResponse]:
    access = get_staff_access(current_user, db_session)
    if not access.organization_admin and not access.managed_store_ids:
        raise HTTPException(status_code=403, detail="Manager role required.")
    query = select(Store).where(Store.organization_id == access.staff.organization_id)
    if not access.organization_admin:
        query = query.where(Store.id.in_(access.managed_store_ids))
    if status is not None:
        query = query.where(Store.status == status)
    if cursor is not None:
        query = query.where(Store.id > cursor)
    stores = db_session.scalars(query.order_by(Store.id).limit(limit + 1)).all()
    result = page([StoreResponse.model_validate(store) for store in stores], limit)
    if len(stores) > limit:
        result.next_cursor = stores[limit - 1].id
    return result


@router.post("/management/stores", response_model=StoreResponse, status_code=201)
def create_store(
    request: StorePayload,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StoreResponse:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    require_writable_organization(access)
    store = Store(organization_id=access.staff.organization_id, **request.model_dump())
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)
    return StoreResponse.model_validate(store)


@router.get("/management/stores/{store_id}")
def read_store(
    store_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    store = store_for_access(store_id, access, db_session)
    regular = db_session.scalars(select(StoreRegularHour).where(StoreRegularHour.store_id == store.id).order_by(StoreRegularHour.day_of_week, StoreRegularHour.opens_at)).all()
    special = db_session.scalars(select(StoreSpecialDay).where(StoreSpecialDay.store_id == store.id).order_by(StoreSpecialDay.business_date)).all()
    return {
        **StoreResponse.model_validate(store).model_dump(mode="json"),
        "regular_hours": [{"day_of_week": hour.day_of_week, "opens_at": hour.opens_at, "closes_at": hour.closes_at} for hour in regular],
        "special_days": [
            {"date": day.business_date, "is_closed": day.is_closed, "reason": day.reason,
             "hours": [{"opens_at": hour.opens_at, "closes_at": hour.closes_at} for hour in db_session.scalars(select(StoreSpecialDayHour).where(StoreSpecialDayHour.special_day_id == day.id)).all()]}
            for day in special
        ],
    }


@router.patch("/management/stores/{store_id}", response_model=StoreResponse)
def update_store(
    store_id: UUID,
    request: StorePatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StoreResponse:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    store = store_for_access(store_id, access, db_session)
    changes = request.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Valid changes are required.")
    if "booking_interval_minutes" in changes:
        ensure_no_future_reservations(store.id, db_session)
    for field, value in changes.items():
        setattr(store, field, value)
    db_session.commit()
    return StoreResponse.model_validate(store)


@router.patch("/management/stores/{store_id}/status", response_model=StoreResponse)
def change_store_status(
    store_id: UUID,
    request: StatusPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StoreResponse:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    store = store_for_access(store_id, access, db_session)
    transitions = {
        StoreStatus.DRAFT: {StoreStatus.ACTIVE},
        StoreStatus.ACTIVE: {StoreStatus.SUSPENDED, StoreStatus.CLOSED},
        StoreStatus.SUSPENDED: {StoreStatus.ACTIVE, StoreStatus.CLOSED},
    }
    if request.status not in transitions.get(store.status, set()):
        raise HTTPException(status_code=409, detail="Invalid store status transition.")
    if request.status == StoreStatus.CLOSED:
        ensure_no_future_reservations(store.id, db_session)
        if db_session.scalar(select(Contract.id).where(
            Contract.status.in_([ContractStatus.PENDING, ContractStatus.SCHEDULED, ContractStatus.ACTIVE, ContractStatus.PAUSED]),
            Contract.plan_snapshot["store_ids"].contains([str(store.id)]),
        ).limit(1)) is not None:
            raise HTTPException(status_code=409, detail="Active contracts must be resolved first.")
    store.status = request.status
    db_session.commit()
    return StoreResponse.model_validate(store)


@router.put("/management/stores/{store_id}/regular-hours")
def replace_regular_hours(
    store_id: UUID,
    request: RegularHoursPayload,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    store_for_access(store_id, access, db_session)
    for weekday in range(1, 8):
        ensure_disjoint([hour for hour in request.hours if hour.day_of_week == weekday])
    ensure_no_future_reservations(store_id, db_session)
    db_session.execute(delete(StoreRegularHour).where(StoreRegularHour.store_id == store_id))
    db_session.add_all(StoreRegularHour(store_id=store_id, **hour.model_dump()) for hour in request.hours)
    db_session.commit()
    return {"hours": request.model_dump(mode="json")["hours"]}


@router.put("/management/stores/{store_id}/special-days/{date}")
def save_special_day(
    store_id: UUID,
    business_date: Annotated[date, Path(alias="date")],
    request: SpecialDayPayload,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    store_for_access(store_id, access, db_session)
    ensure_disjoint(request.hours)
    ensure_no_future_reservations(store_id, db_session)
    day = db_session.scalar(select(StoreSpecialDay).where(StoreSpecialDay.store_id == store_id, StoreSpecialDay.business_date == business_date))
    if day is None:
        day = StoreSpecialDay(store_id=store_id, business_date=business_date, is_closed=request.is_closed, reason=request.reason)
        db_session.add(day)
        db_session.flush()
    else:
        day.is_closed = request.is_closed
        day.reason = request.reason
        db_session.execute(delete(StoreSpecialDayHour).where(StoreSpecialDayHour.special_day_id == day.id))
    db_session.add_all(StoreSpecialDayHour(special_day_id=day.id, **hour.model_dump()) for hour in request.hours)
    db_session.commit()
    return {"date": business_date, **request.model_dump(mode="json")}


@router.delete("/management/stores/{store_id}/special-days/{date}")
def remove_special_day(
    store_id: UUID,
    business_date: Annotated[date, Path(alias="date")],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    store_for_access(store_id, access, db_session)
    day = db_session.scalar(select(StoreSpecialDay).where(StoreSpecialDay.store_id == store_id, StoreSpecialDay.business_date == business_date))
    if day is None:
        raise HTTPException(status_code=404, detail="Special day not found.")
    ensure_no_future_reservations(store_id, db_session)
    db_session.execute(delete(StoreSpecialDayHour).where(StoreSpecialDayHour.special_day_id == day.id))
    db_session.delete(day)
    db_session.commit()
    return {"date": business_date, "hours": "regular"}
