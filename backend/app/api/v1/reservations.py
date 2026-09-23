import base64
import binascii
import json
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.availability import JAPAN_TIMEZONE, as_japan_time, get_availability
from app.api.v1.members import get_member_profile
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.catalog import (
    AvailabilityStatus,
    Menu,
    MenuStatus,
    PlanUsageType,
    StoreMenu,
    TrainerMenu,
)
from app.models.contract import Contract, ContractStatus
from app.models.member import Member, MemberStatus
from app.models.organization import OrganizationStatus
from app.models.reservation import (
    Reservation,
    ReservationStatus,
    ReservationStatusHistory,
    UsageEntry,
    UsageEntryType,
)
from app.models.staff import (
    Staff,
    StaffRole,
    StaffRoleStatus,
    StaffRoleType,
    StaffStatus,
    StaffStoreMembership,
    StaffStoreMembershipStatus,
)
from app.models.store import Store, StoreStatus


router = APIRouter()


class ReservationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    store_id: UUID
    menu_id: UUID
    starts_at: datetime
    trainer_id: UUID | None = None


class NamedResource(BaseModel):
    id: UUID
    name: str


class ReservationCreated(BaseModel):
    id: UUID
    status: ReservationStatus
    store: NamedResource
    menu: NamedResource
    starts_at: datetime
    ends_at: datetime
    trainer: NamedResource


class ReservationListItem(BaseModel):
    id: UUID
    status: ReservationStatus
    store_name: str
    menu_name: str
    starts_at: datetime
    ends_at: datetime
    trainer_name: str


class ReservationPage(BaseModel):
    items: list[ReservationListItem]
    next_cursor: str | None


class ReservationDetail(BaseModel):
    id: UUID
    status: ReservationStatus
    store: NamedResource
    menu: dict[str, str | int | UUID]
    trainer: NamedResource
    starts_at: datetime
    ends_at: datetime
    free_cancellation_until: datetime
    can_cancel: bool


class ReservationCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)


class UsageResult(StrEnum):
    RETURNED = "returned"
    CONSUMED = "consumed"
    NOT_APPLICABLE = "not_applicable"


class ReservationCancelled(BaseModel):
    id: UUID
    status: ReservationStatus
    usage_result: UsageResult


def conflict() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Reservation is no longer available.",
    )


def usage_type(contract: Contract) -> PlanUsageType:
    try:
        return PlanUsageType(contract.plan_snapshot["usage_type"])
    except (KeyError, TypeError, ValueError) as error:
        raise conflict() from error


def available_usage_period(
    db_session: Session, contract_id: UUID, booking_date: date
) -> tuple[date, date] | None:
    contract = db_session.get(Contract, contract_id)
    if contract is not None and contract.plan_snapshot.get("period_type") == "fixed":
        available = db_session.scalar(select(func.coalesce(func.sum(UsageEntry.available_usage_delta), 0)).where(
            UsageEntry.contract_id == contract_id,
        ))
        if available > 0 and contract.starts_on <= booking_date <= contract.ends_on:
            return contract.starts_on, contract.ends_on
        return None
    entries = db_session.execute(
        select(
            UsageEntry.usage_period_starts_on,
            UsageEntry.usage_period_ends_on,
            func.sum(UsageEntry.available_usage_delta),
        )
        .where(
            UsageEntry.contract_id == contract_id,
            UsageEntry.usage_period_starts_on <= booking_date,
            UsageEntry.usage_period_ends_on >= booking_date,
        )
        .group_by(UsageEntry.usage_period_starts_on, UsageEntry.usage_period_ends_on)
        .order_by(UsageEntry.usage_period_starts_on, UsageEntry.usage_period_ends_on)
    ).all()
    for period_start, period_end, available_count in entries:
        if available_count > 0:
            return period_start, period_end
    return None


def reservation_parts(
    db_session: Session, reservation: Reservation
) -> tuple[Store, Menu, Staff]:
    store = db_session.get(Store, reservation.store_id)
    menu = db_session.get(Menu, reservation.menu_id)
    trainer = db_session.get(Staff, reservation.staff_id)
    if store is None or menu is None or trainer is None:
        raise HTTPException(status_code=500, detail="Reservation references missing data.")
    return store, menu, trainer


def cancellation_deadline(reservation: Reservation) -> datetime:
    try:
        hours = int(reservation.reservation_snapshot["free_cancellation_hours"])
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Reservation snapshot is invalid.") from error
    return as_japan_time(reservation.starts_at) - timedelta(hours=hours)


def encode_cursor(starts_at: datetime, reservation_id: UUID) -> str:
    value = json.dumps([as_japan_time(starts_at).astimezone(timezone.utc).isoformat(), str(reservation_id)])
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.b64decode(padded, altchars=b"-_", validate=True))
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("Invalid cursor")
        starts_at = datetime.fromisoformat(value[0])
        if starts_at.tzinfo is None:
            raise ValueError("Invalid cursor timezone")
        return starts_at.astimezone(timezone.utc), UUID(value[1])
    except (ValueError, TypeError, UnicodeError, binascii.Error) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid cursor.",
        ) from error


@router.post("/reservations", response_model=ReservationCreated, status_code=201)
def create_reservation(
    request: ReservationCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReservationCreated:
    member, organization = get_member_profile(current_user, db_session)
    if request.starts_at.tzinfo is None:
        raise HTTPException(status_code=422, detail="starts_at must include a timezone.")

    starts_at = request.starts_at.astimezone(timezone.utc)
    booking_date = starts_at.astimezone(JAPAN_TIMEZONE).date()
    db_session.refresh(member, with_for_update=True)
    if member.status != MemberStatus.ACTIVE or organization.status != OrganizationStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Member is not allowed to book.")
    contracts = db_session.scalars(
        select(Contract)
        .where(
            Contract.member_id == member.id,
            Contract.status.in_((ContractStatus.ACTIVE, ContractStatus.SCHEDULED)),
            Contract.starts_on <= booking_date,
            Contract.ends_on >= booking_date,
        )
        .order_by(Contract.starts_on, Contract.id)
        .with_for_update()
    ).all()
    contract = next(
        (
            candidate
            for candidate in contracts
            if str(request.store_id) in candidate.plan_snapshot.get("store_ids", [])
            and str(request.menu_id) in candidate.plan_snapshot.get("menu_ids", [])
        ),
        None,
    )
    if contract is None:
        raise HTTPException(status_code=404, detail="Booking is unavailable.")

    store = db_session.scalar(
        select(Store).where(
            Store.id == request.store_id,
            Store.organization_id == organization.id,
            Store.status == StoreStatus.ACTIVE,
        )
    )
    menu = db_session.scalar(
        select(Menu)
        .join(StoreMenu, StoreMenu.menu_id == Menu.id)
        .where(
            Menu.id == request.menu_id,
            Menu.organization_id == organization.id,
            Menu.status == MenuStatus.ACTIVE,
            StoreMenu.store_id == request.store_id,
            StoreMenu.status == AvailabilityStatus.ACTIVE,
        )
    )
    if store is None or menu is None:
        raise HTTPException(status_code=404, detail="Booking is unavailable.")
    ends_at = starts_at + timedelta(minutes=menu.duration_minutes)
    if ends_at.astimezone(JAPAN_TIMEZONE).date() != booking_date:
        raise conflict()

    candidates = db_session.execute(
        select(Staff.id, StaffStoreMembership.id)
        .join(StaffStoreMembership, StaffStoreMembership.staff_id == Staff.id)
        .join(StaffRole, StaffRole.store_membership_id == StaffStoreMembership.id)
        .join(TrainerMenu, TrainerMenu.staff_store_membership_id == StaffStoreMembership.id)
        .where(
            Staff.organization_id == organization.id,
            Staff.status == StaffStatus.ACTIVE,
            StaffStoreMembership.store_id == store.id,
            StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
            StaffRole.staff_id == Staff.id,
            StaffRole.role == StaffRoleType.TRAINER,
            StaffRole.status == StaffRoleStatus.ACTIVE,
            TrainerMenu.menu_id == menu.id,
            TrainerMenu.status == AvailabilityStatus.ACTIVE,
        )
        .order_by(Staff.id)
    ).all()
    if request.trainer_id is not None:
        candidates = [row for row in candidates if row[0] == request.trainer_id]
        if not candidates:
            raise HTTPException(status_code=404, detail="Trainer is unavailable.")

    selected_trainer = None
    selected_membership_id = None
    for trainer_id, membership_id in candidates:
        trainer = db_session.scalar(select(Staff).where(Staff.id == trainer_id).with_for_update())
        if trainer is None or trainer.status != StaffStatus.ACTIVE:
            continue
        availability = get_availability(
            store.id,
            booking_date,
            current_user,
            db_session,
            menu.id,
            trainer_id,
        )
        if any(slot.starts_at.astimezone(timezone.utc) == starts_at for slot in availability.slots):
            selected_trainer = trainer
            selected_membership_id = membership_id
            break
    if selected_trainer is None or selected_membership_id is None:
        raise conflict()

    period = None
    if usage_type(contract) == PlanUsageType.LIMITED:
        period = available_usage_period(db_session, contract.id, booking_date)
        if period is None:
            raise conflict()

    reservation = Reservation(
        member_id=member.id,
        contract_id=contract.id,
        store_id=store.id,
        staff_id=selected_trainer.id,
        staff_store_membership_id=selected_membership_id,
        menu_id=menu.id,
        reservation_snapshot={
            "menu_name": menu.name,
            "duration_minutes": menu.duration_minutes,
            "free_cancellation_hours": store.free_cancellation_hours,
        },
        starts_at=starts_at,
        ends_at=ends_at,
    )
    try:
        db_session.add(reservation)
        db_session.flush()
        if period is not None:
            db_session.add(
                UsageEntry(
                    contract_id=contract.id,
                    reservation_id=reservation.id,
                    executed_by_account_id=member.account_id,
                    entry_type=UsageEntryType.HOLD,
                    available_usage_delta=-1,
                    reserved_usage_delta=1,
                    consumed_usage_delta=0,
                    usage_period_starts_on=period[0],
                    usage_period_ends_on=period[1],
                )
            )
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        if getattr(error.orig, "sqlstate", None) == "23P01":
            raise conflict() from error
        raise
    return ReservationCreated(
        id=reservation.id,
        status=reservation.status,
        store=NamedResource(id=store.id, name=store.name),
        menu=NamedResource(id=menu.id, name=menu.name),
        starts_at=as_japan_time(reservation.starts_at),
        ends_at=as_japan_time(reservation.ends_at),
        trainer=NamedResource(id=selected_trainer.id, name=selected_trainer.name),
    )


@router.get("/members/me/reservations", response_model=ReservationPage)
def list_reservations(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    scope: Annotated[str, Query(pattern="^(upcoming|past)$")] = "upcoming",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
) -> ReservationPage:
    member, _ = get_member_profile(current_user, db_session)
    now = datetime.now(timezone.utc)
    query = select(Reservation, Store, Menu, Staff).join(
        Store, Store.id == Reservation.store_id
    ).join(Menu, Menu.id == Reservation.menu_id).join(
        Staff, Staff.id == Reservation.staff_id
    ).where(Reservation.member_id == member.id)
    if scope == "upcoming":
        query = query.where(
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.starts_at > now,
        ).order_by(Reservation.starts_at, Reservation.id)
    else:
        query = query.where(
            or_(
                Reservation.starts_at <= now,
                Reservation.status.in_(
                    (
                        ReservationStatus.COMPLETED,
                        ReservationStatus.NO_SHOW,
                        ReservationStatus.CANCELLED,
                    )
                ),
            )
        ).order_by(Reservation.starts_at.desc(), Reservation.id.desc())
    if cursor is not None:
        cursor_time, cursor_id = decode_cursor(cursor)
        key = or_(
            Reservation.starts_at > cursor_time,
            and_(Reservation.starts_at == cursor_time, Reservation.id > cursor_id),
        ) if scope == "upcoming" else or_(
            Reservation.starts_at < cursor_time,
            and_(Reservation.starts_at == cursor_time, Reservation.id < cursor_id),
        )
        query = query.where(key)
    rows = db_session.execute(query.limit(limit + 1)).all()
    items = [
        ReservationListItem(
            id=reservation.id,
            status=reservation.status,
            store_name=store.name,
            menu_name=reservation.reservation_snapshot.get("menu_name", menu.name),
            starts_at=as_japan_time(reservation.starts_at),
            ends_at=as_japan_time(reservation.ends_at),
            trainer_name=trainer.name,
        )
        for reservation, store, menu, trainer in rows[:limit]
    ]
    next_cursor = (
        encode_cursor(rows[limit - 1][0].starts_at, rows[limit - 1][0].id)
        if len(rows) > limit
        else None
    )
    return ReservationPage(items=items, next_cursor=next_cursor)


@router.get("/members/me/reservations/{reservation_id}", response_model=ReservationDetail)
def get_reservation(
    reservation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReservationDetail:
    member, _ = get_member_profile(current_user, db_session)
    reservation = db_session.scalar(
        select(Reservation).where(
            Reservation.id == reservation_id,
            Reservation.member_id == member.id,
        )
    )
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found.")
    store, menu, trainer = reservation_parts(db_session, reservation)
    return ReservationDetail(
        id=reservation.id,
        status=reservation.status,
        store=NamedResource(id=store.id, name=store.name),
        menu={
            "id": menu.id,
            "name": reservation.reservation_snapshot.get("menu_name", menu.name),
            "duration_minutes": reservation.reservation_snapshot.get(
                "duration_minutes", menu.duration_minutes
            ),
        },
        trainer=NamedResource(id=trainer.id, name=trainer.name),
        starts_at=as_japan_time(reservation.starts_at),
        ends_at=as_japan_time(reservation.ends_at),
        free_cancellation_until=cancellation_deadline(reservation),
        can_cancel=(
            reservation.status == ReservationStatus.CONFIRMED
            and as_japan_time(reservation.starts_at) > datetime.now(JAPAN_TIMEZONE)
        ),
    )


@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationCancelled)
def cancel_reservation(
    reservation_id: UUID,
    request: ReservationCancel,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ReservationCancelled:
    member, _ = get_member_profile(current_user, db_session)
    reservation = db_session.scalar(
        select(Reservation)
        .where(Reservation.id == reservation_id, Reservation.member_id == member.id)
        .with_for_update()
    )
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found.")
    now = datetime.now(JAPAN_TIMEZONE)
    if reservation.status != ReservationStatus.CONFIRMED or as_japan_time(reservation.starts_at) <= now:
        raise conflict()
    contract = db_session.scalar(
        select(Contract).where(Contract.id == reservation.contract_id).with_for_update()
    )
    if contract is None:
        raise conflict()

    result = UsageResult.NOT_APPLICABLE
    if usage_type(contract) == PlanUsageType.LIMITED:
        hold = db_session.scalar(
            select(UsageEntry).where(
                UsageEntry.reservation_id == reservation.id,
                UsageEntry.entry_type == UsageEntryType.HOLD,
            )
        )
        if hold is None:
            raise conflict()
        is_free = now <= cancellation_deadline(reservation)
        result = UsageResult.RETURNED if is_free else UsageResult.CONSUMED
        db_session.add(
            UsageEntry(
                contract_id=contract.id,
                reservation_id=reservation.id,
                executed_by_account_id=member.account_id,
                entry_type=UsageEntryType.RELEASE if is_free else UsageEntryType.CONSUME,
                available_usage_delta=1 if is_free else 0,
                reserved_usage_delta=-1,
                consumed_usage_delta=0 if is_free else 1,
                usage_period_starts_on=hold.usage_period_starts_on,
                usage_period_ends_on=hold.usage_period_ends_on,
            )
        )

    reservation.status = ReservationStatus.CANCELLED
    db_session.add(
        ReservationStatusHistory(
            reservation_id=reservation.id,
            executed_by_account_id=member.account_id,
            previous_status=ReservationStatus.CONFIRMED,
            new_status=ReservationStatus.CANCELLED,
            reason=request.reason or "Cancelled by member.",
        )
    )
    db_session.commit()
    return ReservationCancelled(
        id=reservation.id,
        status=reservation.status,
        usage_result=result,
    )
