from datetime import date, datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.authorization import StaffAccess, get_staff_access, require_writable_organization
from app.api.v1.reservations import usage_type
from app.api.v1.work_shifts import as_utc, date_window
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.catalog import AvailabilityStatus, Menu, PlanUsageType, TrainerMenu
from app.models.contract import Contract
from app.models.member import Member
from app.models.reservation import Reservation, ReservationStatus, ReservationStatusHistory, UsageEntry, UsageEntryType
from app.models.scheduling import UnavailablePeriod, WorkShift, WorkShiftStatus
from app.models.staff import Staff, StaffRole, StaffRoleStatus, StaffRoleType, StaffStatus, StaffStoreMembership, StaffStoreMembershipStatus
from app.models.store import Store


router = APIRouter()


class Reason(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)


class TrainerChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    staff_id: UUID


class ReservationCorrection(Reason):
    status: ReservationStatus


def scoped_reservation(
    reservation_id: UUID, access: StaffAccess, db_session: Session,
    manager_only: bool = False,
) -> Reservation:
    reservation = db_session.scalar(select(Reservation).where(Reservation.id == reservation_id).with_for_update())
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found.")
    store = db_session.get(Store, reservation.store_id)
    if store is None or store.organization_id != access.staff.organization_id:
        raise HTTPException(status_code=404, detail="Reservation not found.")
    if access.organization_admin or reservation.store_id in access.managed_store_ids:
        return reservation
    if not manager_only and reservation.staff_id == access.staff.id and reservation.store_id in access.trainer_store_ids:
        return reservation
    raise HTTPException(status_code=404, detail="Reservation not found.")


def reservation_view(reservation: Reservation, db_session: Session, *, include_member: bool) -> dict:
    store = db_session.get(Store, reservation.store_id)
    menu = db_session.get(Menu, reservation.menu_id)
    trainer = db_session.get(Staff, reservation.staff_id)
    result = {
        "id": reservation.id,
        "status": reservation.status,
        "starts_at": reservation.starts_at,
        "ends_at": reservation.ends_at,
        "store": {"id": store.id, "name": store.name},
        "menu": {"id": menu.id, "name": menu.name, "duration_minutes": menu.duration_minutes},
        "trainer": {"id": trainer.id, "name": trainer.name},
    }
    if include_member:
        member = db_session.get(Member, reservation.member_id)
        result["member"] = {"id": member.id, "name": member.name}
    return result


@router.get("/staff/me/reservations")
def list_staff_reservations(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
    store_id: UUID | None = None,
    scope: Literal["mine", "store"] = "mine",
) -> dict:
    access = get_staff_access(current_user, db_session)
    if not access.organization_admin and not access.managed_store_ids and not access.trainer_store_ids:
        raise HTTPException(status_code=403, detail="Staff role required.")
    allowed_stores = access.managed_store_ids | access.trainer_store_ids
    if store_id is not None and not access.organization_admin and store_id not in allowed_stores:
        raise HTTPException(status_code=404, detail="Store not found.")
    starts_at, ends_at = date_window(from_date, to_date)
    query = select(Reservation).join(Store, Store.id == Reservation.store_id).where(
        Store.organization_id == access.staff.organization_id,
        Reservation.starts_at < ends_at,
        Reservation.ends_at > starts_at,
    )
    if store_id is not None:
        query = query.where(Reservation.store_id == store_id)
    if not access.organization_admin:
        if scope == "mine":
            query = query.where(
                (Reservation.staff_id == access.staff.id)
                | (Reservation.store_id.in_(access.managed_store_ids))
            )
        else:
            query = query.where(Reservation.store_id.in_(allowed_stores))
    reservations = db_session.scalars(query.order_by(Reservation.starts_at, Reservation.id)).all()
    return {"items": [
        reservation_view(
            reservation, db_session,
            include_member=access.organization_admin
            or reservation.store_id in access.managed_store_ids
            or reservation.staff_id == access.staff.id,
        )
        for reservation in reservations
    ]}


@router.get("/staff/me/reservations/{reservation_id}")
def get_staff_reservation(
    reservation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    reservation = scoped_reservation(reservation_id, access, db_session)
    return reservation_view(reservation, db_session, include_member=True)


def consume_reserved_usage(reservation: Reservation, account_id: UUID, db_session: Session) -> None:
    contract = db_session.scalar(select(Contract).where(Contract.id == reservation.contract_id).with_for_update())
    if contract is None:
        raise HTTPException(status_code=409, detail="Contract is unavailable.")
    if usage_type(contract) != PlanUsageType.LIMITED:
        return
    hold = db_session.scalar(select(UsageEntry).where(
        UsageEntry.reservation_id == reservation.id,
        UsageEntry.entry_type == UsageEntryType.HOLD,
    ))
    if hold is None:
        raise HTTPException(status_code=409, detail="Reserved usage is missing.")
    db_session.add(UsageEntry(
        contract_id=contract.id,
        reservation_id=reservation.id,
        executed_by_account_id=account_id,
        entry_type=UsageEntryType.CONSUME,
        available_usage_delta=0,
        reserved_usage_delta=-1,
        consumed_usage_delta=1,
        usage_period_starts_on=hold.usage_period_starts_on,
        usage_period_ends_on=hold.usage_period_ends_on,
    ))


def change_reservation_status(
    reservation_id: UUID,
    target: ReservationStatus,
    current_user: AuthenticatedUser,
    db_session: Session,
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    reservation = scoped_reservation(reservation_id, access, db_session)
    if reservation.status != ReservationStatus.CONFIRMED or as_utc(reservation.starts_at) > datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Reservation is not ready for completion.")
    consume_reserved_usage(reservation, access.account.id, db_session)
    reservation.status = target
    db_session.add(ReservationStatusHistory(
        reservation_id=reservation.id,
        executed_by_account_id=access.account.id,
        previous_status=ReservationStatus.CONFIRMED,
        new_status=target,
        reason="Recorded by staff.",
    ))
    db_session.commit()
    return {"id": reservation.id, "status": reservation.status}


@router.post("/staff/me/reservations/{reservation_id}/complete")
def complete_reservation(
    reservation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    return change_reservation_status(reservation_id, ReservationStatus.COMPLETED, current_user, db_session)


@router.post("/staff/me/reservations/{reservation_id}/no-show")
def mark_no_show(
    reservation_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    return change_reservation_status(reservation_id, ReservationStatus.NO_SHOW, current_user, db_session)


@router.post("/reservations/{reservation_id}/reassign-trainer")
def reassign_trainer(
    reservation_id: UUID,
    request: TrainerChange,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    reservation = scoped_reservation(reservation_id, access, db_session, manager_only=True)
    if reservation.status != ReservationStatus.CONFIRMED or as_utc(reservation.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Reservation cannot be reassigned.")
    trainer = db_session.scalar(select(Staff).where(Staff.id == request.staff_id).with_for_update())
    if trainer is None or trainer.organization_id != access.staff.organization_id or trainer.status != StaffStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Trainer not found.")
    membership = db_session.scalar(select(StaffStoreMembership).where(
        StaffStoreMembership.staff_id == trainer.id,
        StaffStoreMembership.store_id == reservation.store_id,
        StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
    ))
    if membership is None:
        raise HTTPException(status_code=404, detail="Trainer is not assigned to this store.")
    role = db_session.scalar(select(StaffRole.id).where(
        StaffRole.staff_id == trainer.id,
        StaffRole.store_membership_id == membership.id,
        StaffRole.role == StaffRoleType.TRAINER,
        StaffRole.status == StaffRoleStatus.ACTIVE,
    ))
    menu = db_session.get(TrainerMenu, (membership.id, reservation.menu_id))
    if role is None or menu is None or menu.status != AvailabilityStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Trainer cannot deliver this menu.")
    shift = db_session.scalar(select(WorkShift.id).where(
        WorkShift.staff_id == trainer.id,
        WorkShift.staff_store_membership_id == membership.id,
        WorkShift.status == WorkShiftStatus.SCHEDULED,
        WorkShift.starts_at <= reservation.starts_at,
        WorkShift.ends_at >= reservation.ends_at,
    ).limit(1))
    blocked = db_session.scalar(select(UnavailablePeriod.id).join(WorkShift, WorkShift.id == UnavailablePeriod.work_shift_id).where(
        WorkShift.staff_id == trainer.id,
        UnavailablePeriod.starts_at < reservation.ends_at,
        UnavailablePeriod.ends_at > reservation.starts_at,
    ).limit(1))
    overlap = db_session.scalar(select(Reservation.id).where(
        Reservation.id != reservation.id,
        Reservation.staff_id == trainer.id,
        Reservation.status == ReservationStatus.CONFIRMED,
        Reservation.starts_at < reservation.ends_at,
        Reservation.ends_at > reservation.starts_at,
    ).limit(1))
    if shift is None or blocked is not None or overlap is not None:
        raise HTTPException(status_code=409, detail="Trainer is unavailable at this time.")
    reservation.staff_id = trainer.id
    reservation.staff_store_membership_id = membership.id
    try:
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="Trainer became unavailable.") from error
    return {"id": reservation.id, "trainer": {"id": trainer.id, "name": trainer.name}}


@router.post("/staff/me/reservations/{reservation_id}/cancel")
def cancel_for_store(
    reservation_id: UUID,
    request: Reason,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    reservation = scoped_reservation(reservation_id, access, db_session)
    if reservation.status != ReservationStatus.CONFIRMED or as_utc(reservation.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=409, detail="Reservation cannot be cancelled.")
    contract = db_session.scalar(select(Contract).where(Contract.id == reservation.contract_id).with_for_update())
    if contract is None:
        raise HTTPException(status_code=409, detail="Contract is unavailable.")
    if usage_type(contract) == PlanUsageType.LIMITED:
        hold = db_session.scalar(select(UsageEntry).where(
            UsageEntry.reservation_id == reservation.id,
            UsageEntry.entry_type == UsageEntryType.HOLD,
        ))
        if hold is None:
            raise HTTPException(status_code=409, detail="Reserved usage is missing.")
        db_session.add(UsageEntry(
            contract_id=contract.id,
            reservation_id=reservation.id,
            executed_by_account_id=access.account.id,
            entry_type=UsageEntryType.RELEASE,
            available_usage_delta=1,
            reserved_usage_delta=-1,
            consumed_usage_delta=0,
            usage_period_starts_on=hold.usage_period_starts_on,
            usage_period_ends_on=hold.usage_period_ends_on,
            reason=request.reason,
        ))
    reservation.status = ReservationStatus.CANCELLED
    db_session.add(ReservationStatusHistory(
        reservation_id=reservation.id,
        executed_by_account_id=access.account.id,
        previous_status=ReservationStatus.CONFIRMED,
        new_status=ReservationStatus.CANCELLED,
        reason=request.reason,
    ))
    db_session.commit()
    return {"id": reservation.id, "status": reservation.status}


@router.post("/management/reservations/{reservation_id}/correct-status")
def correct_reservation_status(
    reservation_id: UUID,
    request: ReservationCorrection,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    reservation = scoped_reservation(reservation_id, access, db_session, manager_only=True)
    if request.status == reservation.status:
        raise HTTPException(status_code=409, detail="Reservation status is unchanged.")
    if request.status == ReservationStatus.CONFIRMED:
        if as_utc(reservation.starts_at) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=409, detail="Past reservations cannot be reconfirmed.")
        overlap = db_session.scalar(select(Reservation.id).where(
            Reservation.id != reservation.id,
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.starts_at < reservation.ends_at,
            Reservation.ends_at > reservation.starts_at,
            or_(Reservation.staff_id == reservation.staff_id,
                Reservation.member_id == reservation.member_id),
        ).limit(1))
        if overlap is not None:
            raise HTTPException(status_code=409, detail="Reservation slot is already occupied.")
    contract = db_session.scalar(select(Contract).where(Contract.id == reservation.contract_id).with_for_update())
    if contract is None:
        raise HTTPException(status_code=409, detail="Contract is unavailable.")
    if usage_type(contract) == PlanUsageType.LIMITED:
        hold = db_session.scalar(select(UsageEntry).where(
            UsageEntry.reservation_id == reservation.id,
            UsageEntry.entry_type == UsageEntryType.HOLD,
        ))
        if hold is None:
            raise HTTPException(status_code=409, detail="Reservation usage history is missing.")
        current_available, current_reserved, current_consumed = db_session.execute(select(
            func.coalesce(func.sum(UsageEntry.available_usage_delta), 0),
            func.coalesce(func.sum(UsageEntry.reserved_usage_delta), 0),
            func.coalesce(func.sum(UsageEntry.consumed_usage_delta), 0),
        ).where(UsageEntry.reservation_id == reservation.id)).one()
        target = {
            ReservationStatus.CONFIRMED: (-1, 1, 0),
            ReservationStatus.COMPLETED: (-1, 0, 1),
            ReservationStatus.NO_SHOW: (-1, 0, 1),
            ReservationStatus.CANCELLED: (0, 0, 0),
        }[request.status]
        deltas = (target[0] - current_available, target[1] - current_reserved,
                  target[2] - current_consumed)
        if deltas != (0, 0, 0):
            db_session.add(UsageEntry(
                contract_id=contract.id, reservation_id=reservation.id,
                executed_by_account_id=access.account.id,
                entry_type=UsageEntryType.ADJUSTMENT,
                available_usage_delta=deltas[0], reserved_usage_delta=deltas[1],
                consumed_usage_delta=deltas[2],
                usage_period_starts_on=hold.usage_period_starts_on,
                usage_period_ends_on=hold.usage_period_ends_on,
                reason=request.reason,
            ))
    previous = reservation.status
    reservation.status = request.status
    db_session.add(ReservationStatusHistory(
        reservation_id=reservation.id, executed_by_account_id=access.account.id,
        previous_status=previous, new_status=request.status, reason=request.reason,
    ))
    try:
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="Reservation status conflicts with another booking.") from error
    return {"id": reservation.id, "status": reservation.status}
