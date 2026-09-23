import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.me import get_active_account
from app.api.v1.members import get_member_profile
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.catalog import (
    AvailabilityStatus,
    Menu,
    MenuStatus,
    Plan,
    PlanMenu,
    PlanStatus,
    PlanStore,
    PlanUsageType,
    StoreMenu,
)
from app.models.contract import Contract, ContractAdjustmentHistory, ContractStatus, ContractStatusHistory
from app.models.member import Member, MemberStatus
from app.models.organization import Organization, OrganizationStatus
from app.models.reservation import Reservation, ReservationStatus, UsageEntry, UsageEntryType
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
JAPAN_TIMEZONE = ZoneInfo("Asia/Tokyo")
ACTIVE_CONTRACT_STATUSES = (
    ContractStatus.PENDING,
    ContractStatus.SCHEDULED,
    ContractStatus.ACTIVE,
    ContractStatus.PAUSED,
)


class ContractApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID
    starts_on: date


class ContractResponse(BaseModel):
    id: UUID
    status: ContractStatus
    plan_name: str
    starts_on: date
    ends_on: date
    usage_type: PlanUsageType
    usage_limit: int | None


class ContractDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)


class ContractRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)


class ContractReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=1000)


class ContractAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=1000)
    ends_on: date | None = None
    usage_delta: int | None = None

    @model_validator(mode="after")
    def exactly_one_adjustment(self):
        if (self.ends_on is None) == (self.usage_delta is None):
            raise ValueError("Specify either ends_on or usage_delta.")
        if self.usage_delta == 0:
            raise ValueError("usage_delta must not be zero.")
        return self


def contract_usage(contract: Contract, db_session: Session) -> dict:
    if contract.plan_snapshot.get("usage_type") == PlanUsageType.UNLIMITED.value:
        return {"type": "unlimited"}
    available, reserved = db_session.execute(
        select(
            func.coalesce(func.sum(UsageEntry.available_usage_delta), 0),
            func.coalesce(func.sum(UsageEntry.reserved_usage_delta), 0),
        ).where(UsageEntry.contract_id == contract.id)
    ).one()
    return {
        "type": "count_based",
        "available_count": available,
        "reserved_count": reserved,
    }


def detailed_contract(contract: Contract, db_session: Session) -> dict:
    return {
        "id": contract.id,
        "status": contract.status,
        "plan_name": contract.plan_snapshot["name"],
        "price_yen": contract.plan_snapshot.get("price_yen"),
        "starts_on": contract.starts_on,
        "ends_on": contract.ends_on,
        "usage": contract_usage(contract, db_session),
        "plan_snapshot": contract.plan_snapshot,
    }


def today_in_japan() -> date:
    return datetime.now(JAPAN_TIMEZONE).date()


def period_end(starts_on: date, months: int) -> date:
    month_index = starts_on.month - 1 + months
    year = starts_on.year + month_index // 12
    month = month_index % 12 + 1
    day = min(starts_on.day, calendar.monthrange(year, month)[1])
    return date(year, month, day) - timedelta(days=1)


def contract_response(contract: Contract) -> ContractResponse:
    return ContractResponse(
        id=contract.id,
        status=contract.status,
        plan_name=str(contract.plan_snapshot["name"]),
        starts_on=contract.starts_on,
        ends_on=contract.ends_on,
        usage_type=PlanUsageType(contract.plan_snapshot["usage_type"]),
        usage_limit=contract.plan_snapshot.get("usage_limit"),
    )


def eligible_plan_scope(
    db_session: Session, plan: Plan, organization_id: UUID
) -> tuple[list[UUID], list[UUID]]:
    store_ids = db_session.scalars(
        select(PlanStore.store_id)
        .join(Store, Store.id == PlanStore.store_id)
        .where(
            PlanStore.plan_id == plan.id,
            PlanStore.status == AvailabilityStatus.ACTIVE,
            Store.organization_id == organization_id,
            Store.status == StoreStatus.ACTIVE,
        )
        .order_by(PlanStore.store_id)
    ).all()
    if not store_ids:
        return [], []
    menu_ids = db_session.scalars(
        select(PlanMenu.menu_id)
        .join(Menu, Menu.id == PlanMenu.menu_id)
        .join(
            StoreMenu,
            StoreMenu.menu_id == PlanMenu.menu_id,
        )
        .where(
            PlanMenu.plan_id == plan.id,
            PlanMenu.status == AvailabilityStatus.ACTIVE,
            Menu.organization_id == organization_id,
            Menu.status == MenuStatus.ACTIVE,
            StoreMenu.store_id.in_(store_ids),
            StoreMenu.status == AvailabilityStatus.ACTIVE,
        )
        .distinct()
        .order_by(PlanMenu.menu_id)
    ).all()
    if not menu_ids:
        return [], []
    bookable_store_ids = db_session.scalars(
        select(StoreMenu.store_id)
        .where(
            StoreMenu.store_id.in_(store_ids),
            StoreMenu.menu_id.in_(menu_ids),
            StoreMenu.status == AvailabilityStatus.ACTIVE,
        )
        .distinct()
        .order_by(StoreMenu.store_id)
    ).all()
    return bookable_store_ids, menu_ids


@router.post("/members/me/contracts", response_model=ContractResponse, status_code=201)
def apply_for_contract(
    request: ContractApplication,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContractResponse:
    member, organization = get_member_profile(current_user, db_session)
    db_session.refresh(member, with_for_update=True)
    if member.status != MemberStatus.ACTIVE or organization.status != OrganizationStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Member is not allowed to apply.")
    if request.starts_on < today_in_japan():
        raise HTTPException(status_code=422, detail="starts_on must not be in the past.")

    plan = db_session.scalar(
        select(Plan).where(
            Plan.id == request.plan_id,
            Plan.organization_id == organization.id,
            Plan.status == PlanStatus.ACTIVE,
        )
    )
    if plan is None:
        raise HTTPException(status_code=409, detail="Plan is unavailable.")
    store_ids, menu_ids = eligible_plan_scope(db_session, plan, organization.id)
    if not store_ids or not menu_ids:
        raise HTTPException(status_code=409, detail="Plan has no bookable store and menu.")

    ends_on = period_end(request.starts_on, plan.period_months)
    existing = db_session.scalar(
        select(Contract.id).where(
            Contract.member_id == member.id,
            Contract.status.in_(ACTIVE_CONTRACT_STATUSES),
            Contract.starts_on <= ends_on,
            Contract.ends_on >= request.starts_on,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Contract period overlaps another application.")

    contract = Contract(
        member_id=member.id,
        plan_id=plan.id,
        starts_on=request.starts_on,
        ends_on=ends_on,
        status=ContractStatus.PENDING,
        plan_snapshot={
            "name": plan.name,
            "price_yen": plan.price_yen,
            "usage_type": plan.usage_type.value,
            "usage_limit": plan.usage_limit,
            "period_type": plan.period_type.value,
            "period_months": plan.period_months,
            "carryover_limit": plan.carryover_limit,
            "store_ids": [str(store_id) for store_id in store_ids],
            "menu_ids": [str(menu_id) for menu_id in menu_ids],
        },
    )
    try:
        db_session.add(contract)
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        if getattr(error.orig, "sqlstate", None) == "23P01":
            raise HTTPException(status_code=409, detail="Contract period overlaps another application.") from error
        raise
    return contract_response(contract)


def management_contract(
    contract_id: UUID, current_user: AuthenticatedUser, db_session: Session
) -> tuple[Contract, Staff]:
    account = get_active_account(current_user, db_session)
    staff = db_session.scalar(select(Staff).where(Staff.account_id == account.id))
    if staff is None or staff.status != StaffStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Staff access is required.")
    contract = db_session.scalar(
        select(Contract).where(Contract.id == contract_id).with_for_update()
    )
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    member = db_session.get(Member, contract.member_id)
    organization = db_session.get(Organization, staff.organization_id)
    if member is None or member.organization_id != staff.organization_id:
        raise HTTPException(status_code=404, detail="Contract not found.")
    if organization is None or organization.status != OrganizationStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Organization is unavailable.")

    roles = db_session.execute(
        select(
            StaffRole.role,
            StaffRole.store_membership_id,
            StaffStoreMembership.store_id,
            StaffStoreMembership.status,
            StaffStoreMembership.staff_id,
        )
        .outerjoin(
            StaffStoreMembership,
            StaffStoreMembership.id == StaffRole.store_membership_id,
        )
        .where(
            StaffRole.staff_id == staff.id,
            StaffRole.status == StaffRoleStatus.ACTIVE,
        )
    ).all()
    allowed_stores = set(contract.plan_snapshot.get("store_ids", []))
    permitted = any(
        (role == StaffRoleType.ORGANIZATION_ADMIN and membership_id is None)
        or (
            role == StaffRoleType.STORE_ADMIN
            and membership_id is not None
            and membership_status == StaffStoreMembershipStatus.ACTIVE
            and membership_staff_id == staff.id
            and str(store_id) in allowed_stores
        )
        for role, membership_id, store_id, membership_status, membership_staff_id in roles
    )
    if not permitted:
        raise HTTPException(status_code=403, detail="Contract review is not permitted.")
    return contract, staff


@router.post("/management/contracts/{contract_id}/approve", response_model=ContractResponse)
def approve_contract(
    contract_id: UUID,
    request: ContractDecision,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContractResponse:
    contract, staff = management_contract(contract_id, current_user, db_session)
    if contract.status != ContractStatus.PENDING or contract.ends_on < today_in_japan():
        raise HTTPException(status_code=409, detail="Contract cannot be approved.")
    contract.status = (
        ContractStatus.SCHEDULED
        if contract.starts_on > today_in_japan()
        else ContractStatus.ACTIVE
    )
    db_session.add(
        ContractStatusHistory(
            contract_id=contract.id,
            executed_by_account_id=staff.account_id,
            previous_status=ContractStatus.PENDING,
            new_status=contract.status,
            reason=request.reason or "Approved by management.",
        )
    )
    if PlanUsageType(contract.plan_snapshot["usage_type"]) == PlanUsageType.LIMITED:
        db_session.add(
            UsageEntry(
                contract_id=contract.id,
                executed_by_account_id=staff.account_id,
                entry_type=UsageEntryType.GRANT,
                available_usage_delta=int(contract.plan_snapshot["usage_limit"]),
                reserved_usage_delta=0,
                consumed_usage_delta=0,
                usage_period_starts_on=contract.starts_on,
                usage_period_ends_on=contract.ends_on,
            )
        )
    db_session.commit()
    return contract_response(contract)


@router.post("/management/contracts/{contract_id}/reject", response_model=ContractResponse)
def reject_contract(
    contract_id: UUID,
    request: ContractRejection,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContractResponse:
    contract, staff = management_contract(contract_id, current_user, db_session)
    if contract.status != ContractStatus.PENDING:
        raise HTTPException(status_code=409, detail="Contract cannot be rejected.")
    contract.status = ContractStatus.REJECTED
    db_session.add(
        ContractStatusHistory(
            contract_id=contract.id,
            executed_by_account_id=staff.account_id,
            previous_status=ContractStatus.PENDING,
            new_status=ContractStatus.REJECTED,
            reason=request.reason,
        )
    )
    db_session.commit()
    return contract_response(contract)


@router.get("/members/me/contracts")
def list_my_contracts(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    scope: Literal["current", "history"] = "current",
) -> dict:
    member, _ = get_member_profile(current_user, db_session)
    statuses = (
        ACTIVE_CONTRACT_STATUSES
        if scope == "current"
        else (ContractStatus.TERMINATED, ContractStatus.EXPIRED, ContractStatus.REJECTED)
    )
    contracts = db_session.scalars(
        select(Contract)
        .where(Contract.member_id == member.id, Contract.status.in_(statuses))
        .order_by(Contract.starts_on.desc(), Contract.id.desc())
    ).all()
    return {"items": [detailed_contract(contract, db_session) for contract in contracts]}


@router.get("/management/contracts")
def list_management_contracts(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    store_id: UUID | None = None,
    member_id: UUID | None = None,
    status: ContractStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> dict:
    from app.api.v1.authorization import get_staff_access

    access = get_staff_access(current_user, db_session)
    allowed_stores = access.managed_store_ids
    if not access.organization_admin and not allowed_stores:
        raise HTTPException(status_code=403, detail="Manager role required.")
    if store_id is not None and not access.organization_admin and store_id not in allowed_stores:
        raise HTTPException(status_code=404, detail="Store not found.")
    query = select(Contract).join(Member, Member.id == Contract.member_id).where(
        Member.organization_id == access.staff.organization_id
    )
    if member_id is not None:
        query = query.where(Contract.member_id == member_id)
    if status is not None:
        query = query.where(Contract.status == status)
    if cursor is not None:
        query = query.where(Contract.id > cursor)
    contracts = db_session.scalars(query.order_by(Contract.id)).all()
    visible = []
    for contract in contracts:
        plan_stores = set(contract.plan_snapshot.get("store_ids", []))
        if store_id is not None and str(store_id) not in plan_stores:
            continue
        if not access.organization_admin and not plan_stores.intersection(str(store) for store in allowed_stores):
            continue
        visible.append(detailed_contract(contract, db_session))
        if len(visible) > limit:
            break
    return {
        "items": visible[:limit],
        "next_cursor": visible[limit - 1]["id"] if len(visible) > limit else None,
    }


@router.get("/management/contracts/{contract_id}")
def get_management_contract(
    contract_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    contract, _ = management_contract(contract_id, current_user, db_session)
    history = db_session.scalars(
        select(ContractStatusHistory)
        .where(ContractStatusHistory.contract_id == contract.id)
        .order_by(ContractStatusHistory.created_at, ContractStatusHistory.id)
    ).all()
    return {
        **detailed_contract(contract, db_session),
        "history": [
            {
                "previous_status": event.previous_status,
                "new_status": event.new_status,
                "reason": event.reason,
                "created_at": event.created_at,
            }
            for event in history
        ],
    }


def change_contract_status(
    contract_id: UUID,
    reason: str,
    new_status: ContractStatus,
    allowed_previous: set[ContractStatus],
    current_user: AuthenticatedUser,
    db_session: Session,
) -> ContractResponse:
    contract, staff = management_contract(contract_id, current_user, db_session)
    if contract.status not in allowed_previous:
        raise HTTPException(status_code=409, detail="Invalid contract status transition.")
    if new_status in (ContractStatus.PAUSED, ContractStatus.TERMINATED):
        future_reservation = db_session.scalar(
            select(Reservation.id).where(
                Reservation.contract_id == contract.id,
                Reservation.status == ReservationStatus.CONFIRMED,
                Reservation.starts_at > datetime.now(timezone.utc),
            ).limit(1)
        )
        if future_reservation is not None:
            raise HTTPException(status_code=409, detail="Future reservations must be resolved first.")
    if new_status == ContractStatus.ACTIVE:
        if not contract.starts_on <= today_in_japan() <= contract.ends_on:
            raise HTTPException(status_code=409, detail="Contract period is not active.")
        store_ids = [UUID(store_id) for store_id in contract.plan_snapshot.get("store_ids", [])]
        active_store = db_session.scalar(select(Store.id).where(
            Store.id.in_(store_ids), Store.status == StoreStatus.ACTIVE
        ).limit(1))
        if active_store is None:
            raise HTTPException(status_code=409, detail="No active store remains for this contract.")
    previous = contract.status
    contract.status = new_status
    db_session.add(ContractStatusHistory(
        contract_id=contract.id,
        executed_by_account_id=staff.account_id,
        previous_status=previous,
        new_status=new_status,
        reason=reason,
    ))
    db_session.commit()
    return contract_response(contract)


@router.post("/management/contracts/{contract_id}/pause", response_model=ContractResponse)
def pause_contract(
    contract_id: UUID,
    request: ContractReason,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContractResponse:
    return change_contract_status(contract_id, request.reason, ContractStatus.PAUSED, {ContractStatus.ACTIVE}, current_user, db_session)


@router.post("/management/contracts/{contract_id}/resume", response_model=ContractResponse)
def resume_contract(
    contract_id: UUID,
    request: ContractReason,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContractResponse:
    return change_contract_status(contract_id, request.reason, ContractStatus.ACTIVE, {ContractStatus.PAUSED}, current_user, db_session)


@router.post("/management/contracts/{contract_id}/terminate", response_model=ContractResponse)
def terminate_contract(
    contract_id: UUID,
    request: ContractReason,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> ContractResponse:
    return change_contract_status(contract_id, request.reason, ContractStatus.TERMINATED, {ContractStatus.SCHEDULED, ContractStatus.ACTIVE, ContractStatus.PAUSED}, current_user, db_session)


@router.post("/management/contracts/{contract_id}/adjustments")
def adjust_contract(
    contract_id: UUID,
    request: ContractAdjustment,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    contract, staff = management_contract(contract_id, current_user, db_session)
    if contract.status not in (ContractStatus.SCHEDULED, ContractStatus.ACTIVE, ContractStatus.PAUSED):
        raise HTTPException(status_code=409, detail="Contract cannot be adjusted.")
    if request.ends_on is not None:
        if request.ends_on < contract.starts_on:
            raise HTTPException(status_code=422, detail="ends_on is before starts_on.")
        confirmed_reservations = db_session.scalars(select(Reservation).where(
            Reservation.contract_id == contract.id,
            Reservation.status == ReservationStatus.CONFIRMED,
        )).all()
        if any(reservation.starts_at.astimezone(JAPAN_TIMEZONE).date() > request.ends_on
               for reservation in confirmed_reservations):
            raise HTTPException(status_code=409, detail="Confirmed reservations fall outside the new period.")
        other = db_session.scalar(select(Contract.id).where(
            Contract.id != contract.id,
            Contract.member_id == contract.member_id,
            Contract.status.in_(ACTIVE_CONTRACT_STATUSES),
            Contract.starts_on <= request.ends_on,
            Contract.ends_on >= contract.starts_on,
        ).limit(1))
        if other is not None:
            raise HTTPException(status_code=409, detail="Contract period overlaps another contract.")
        previous = contract.ends_on
        contract.ends_on = request.ends_on
        db_session.add(ContractAdjustmentHistory(
            contract_id=contract.id, executed_by_account_id=staff.account_id,
            previous_ends_on=previous, new_ends_on=request.ends_on, reason=request.reason,
        ))
    else:
        if contract.plan_snapshot.get("usage_type") != PlanUsageType.LIMITED.value:
            raise HTTPException(status_code=409, detail="Unlimited contracts have no usage balance.")
        period = db_session.execute(select(
            UsageEntry.usage_period_starts_on, UsageEntry.usage_period_ends_on,
        ).where(UsageEntry.contract_id == contract.id).order_by(
            UsageEntry.usage_period_starts_on.desc()
        ).limit(1)).one_or_none()
        if period is None:
            raise HTTPException(status_code=409, detail="Usage period is not initialized.")
        available = db_session.scalar(select(func.coalesce(func.sum(UsageEntry.available_usage_delta), 0)).where(
            UsageEntry.contract_id == contract.id,
            UsageEntry.usage_period_starts_on == period[0],
            UsageEntry.usage_period_ends_on == period[1],
        ))
        if available + request.usage_delta < 0:
            raise HTTPException(status_code=409, detail="Usage balance cannot be negative.")
        db_session.add(UsageEntry(
            contract_id=contract.id, executed_by_account_id=staff.account_id,
            entry_type=UsageEntryType.ADJUSTMENT,
            available_usage_delta=request.usage_delta,
            reserved_usage_delta=0, consumed_usage_delta=0,
            usage_period_starts_on=period[0], usage_period_ends_on=period[1],
            reason=request.reason,
        ))
        db_session.add(ContractAdjustmentHistory(
            contract_id=contract.id, executed_by_account_id=staff.account_id,
            usage_delta=request.usage_delta, reason=request.reason,
        ))
    db_session.commit()
    return detailed_contract(contract, db_session)
