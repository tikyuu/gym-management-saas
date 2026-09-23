from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.me import get_active_account
from zoneinfo import ZoneInfo
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.organization import (
    AdminVerification, Organization, OrganizationStatus,
    OrganizationStatusHistory, SystemAdmin, SystemAdminAudit,
)
from app.models.contract import Contract, ContractStatus
from app.models.member import Member
from app.models.reservation import Reservation, ReservationStatus
from app.models.staff import Staff, StaffRole, StaffRoleStatus, StaffRoleType, StaffStatus, StaffStatusHistory, StaffStoreMembership, StaffStoreMembershipStatus
from app.models.store import Store
from app.models.user_account import UserAccount, UserAccountStatus
from app.services.cognito_admin import CognitoAdmin, get_cognito_admin
from app.settings import Settings


router = APIRouter()


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)


class OrganizationChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: OrganizationStatus
    reason: str = Field(min_length=1, max_length=1000)


class AdminInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr


class AdminRecovery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    staff_id: UUID
    verification_reference: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=1000)


def require_system_admin(current_user: AuthenticatedUser, db_session: Session) -> tuple[UserAccount, SystemAdmin]:
    if current_user.user_pool_id != Settings().system_admin_user_pool_id:
        raise HTTPException(status_code=403, detail="System administrator access required.")
    account = get_active_account(current_user, db_session)
    admin = db_session.scalar(select(SystemAdmin).where(SystemAdmin.account_id == account.id))
    if admin is None:
        raise HTTPException(status_code=403, detail="System administrator access required.")
    return account, admin


def organization_or_404(organization_id: UUID, db_session: Session, *, lock: bool = False) -> Organization:
    query = select(Organization).where(Organization.id == organization_id)
    organization = db_session.scalar(query.with_for_update() if lock else query)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return organization


@router.get("/system-admin/me")
def system_admin_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    _, admin = require_system_admin(current_user, db_session)
    return {"id": admin.id, "name": admin.name, "user_type": "system_admin"}


@router.get("/system-admin/organizations")
def list_organizations(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    status: OrganizationStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> dict:
    require_system_admin(current_user, db_session)
    query = select(Organization)
    if status is not None:
        query = query.where(Organization.status == status)
    if cursor is not None:
        query = query.where(Organization.id > cursor)
    organizations = db_session.scalars(query.order_by(Organization.id).limit(limit + 1)).all()
    return {
        "items": [{"id": item.id, "name": item.name, "status": item.status} for item in organizations[:limit]],
        "next_cursor": organizations[limit - 1].id if len(organizations) > limit else None,
    }


@router.post("/system-admin/organizations", status_code=201)
def create_organization(
    request: OrganizationCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    require_system_admin(current_user, db_session)
    if db_session.scalar(select(Organization.id).where(Organization.name == request.name)) is not None:
        raise HTTPException(status_code=409, detail="Organization already exists.")
    organization = Organization(name=request.name)
    db_session.add(organization)
    db_session.commit()
    return {"id": organization.id, "status": organization.status}


@router.get("/system-admin/organizations/{organization_id}")
def get_organization(
    organization_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    require_system_admin(current_user, db_session)
    organization = organization_or_404(organization_id, db_session)
    stores = db_session.scalars(select(Store).where(Store.organization_id == organization.id)).all()
    histories = db_session.scalars(select(OrganizationStatusHistory).where(
        OrganizationStatusHistory.organization_id == organization.id
    ).order_by(OrganizationStatusHistory.created_at, OrganizationStatusHistory.id)).all()
    return {
        "id": organization.id, "name": organization.name, "status": organization.status,
        "stores": [{"id": store.id, "name": store.name, "status": store.status} for store in stores],
        "history": [{"previous_status": event.previous_status, "new_status": event.new_status,
                     "reason": event.reason, "created_at": event.created_at} for event in histories],
    }


@router.patch("/system-admin/organizations/{organization_id}/status")
def change_organization_status(
    organization_id: UUID,
    request: OrganizationChange,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    account, _ = require_system_admin(current_user, db_session)
    organization = organization_or_404(organization_id, db_session, lock=True)
    allowed = {
        OrganizationStatus.PREPARING: {OrganizationStatus.ACTIVE},
        OrganizationStatus.ACTIVE: {OrganizationStatus.SUSPENDED, OrganizationStatus.TERMINATED},
        OrganizationStatus.SUSPENDED: {OrganizationStatus.ACTIVE, OrganizationStatus.TERMINATED},
        OrganizationStatus.TERMINATED: set(),
    }
    if request.status not in allowed[organization.status]:
        raise HTTPException(status_code=409, detail="Invalid organization status transition.")
    if request.status in (OrganizationStatus.SUSPENDED, OrganizationStatus.TERMINATED):
        future_reservation = db_session.scalar(select(Reservation.id).join(
            Store, Store.id == Reservation.store_id,
        ).where(
            Store.organization_id == organization.id,
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.starts_at > datetime.now(timezone.utc),
        ).limit(1))
        if future_reservation is not None:
            raise HTTPException(status_code=409, detail="Future reservations must be resolved first.")
    if request.status == OrganizationStatus.TERMINATED:
        active_contract = db_session.scalar(select(Contract.id).join(
            Member, Member.id == Contract.member_id,
        ).where(
            Member.organization_id == organization.id,
            Contract.status.in_(
            (ContractStatus.PENDING, ContractStatus.SCHEDULED,
             ContractStatus.ACTIVE, ContractStatus.PAUSED)
        )).limit(1))
        if active_contract is not None:
            raise HTTPException(status_code=409, detail="Active contracts must be resolved first.")
    if request.status == OrganizationStatus.ACTIVE:
        admin_ids = select(Staff.id).join(StaffRole, StaffRole.staff_id == Staff.id).where(
            Staff.organization_id == organization.id,
            Staff.status == StaffStatus.ACTIVE,
            StaffRole.role == StaffRoleType.ORGANIZATION_ADMIN,
            StaffRole.status == StaffRoleStatus.ACTIVE,
        )
        store_manager = db_session.scalar(select(StaffRole.id).join(
            StaffStoreMembership, StaffStoreMembership.id == StaffRole.store_membership_id
        ).join(Store, Store.id == StaffStoreMembership.store_id).where(
            Store.organization_id == organization.id,
            StaffStoreMembership.staff_id.in_(admin_ids),
            StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
            StaffRole.role == StaffRoleType.STORE_ADMIN,
            StaffRole.status == StaffRoleStatus.ACTIVE,
        ))
        if store_manager is None:
            raise HTTPException(status_code=409, detail="Initial administrator and store setup are incomplete.")
    old_status = organization.status
    organization.status = request.status
    db_session.add(OrganizationStatusHistory(
        organization_id=organization.id, executed_by_account_id=account.id,
        previous_status=old_status, new_status=request.status, reason=request.reason,
    ))
    db_session.commit()
    return {"id": organization.id, "status": organization.status}


@router.post("/system-admin/organizations/{organization_id}/initial-admin", status_code=201)
def invite_initial_admin(
    organization_id: UUID,
    request: AdminInvite,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    cognito: Annotated[CognitoAdmin, Depends(get_cognito_admin)],
) -> dict:
    require_system_admin(current_user, db_session)
    organization = organization_or_404(organization_id, db_session, lock=True)
    if organization.status != OrganizationStatus.PREPARING:
        raise HTTPException(status_code=409, detail="Organization is not preparing.")
    if db_session.scalar(select(Staff.id).join(StaffRole, StaffRole.staff_id == Staff.id).where(
        Staff.organization_id == organization.id, StaffRole.role == StaffRoleType.ORGANIZATION_ADMIN,
    )) is not None:
        raise HTTPException(status_code=409, detail="Initial administrator already exists.")
    pool_id = Settings().staff_user_pool_id
    subject = cognito.invite(pool_id, str(request.email))
    account = UserAccount(user_pool_id=pool_id, cognito_sub=subject)
    db_session.add(account)
    try:
        db_session.flush()
        staff = Staff(organization_id=organization.id, account_id=account.id, name=request.name)
        db_session.add(staff)
        db_session.flush()
        db_session.add(StaffRole(staff_id=staff.id, role=StaffRoleType.ORGANIZATION_ADMIN))
        db_session.commit()
    except Exception:
        db_session.rollback()
        cognito.delete(pool_id, subject)
        raise
    return {"id": staff.id, "status": staff.status}


@router.post("/system-admin/organizations/{organization_id}/recover-admin")
def recover_admin(
    organization_id: UUID,
    request: AdminRecovery,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    cognito: Annotated[CognitoAdmin, Depends(get_cognito_admin)],
) -> dict:
    account, _ = require_system_admin(current_user, db_session)
    organization = organization_or_404(organization_id, db_session, lock=True)
    staff = db_session.scalar(select(Staff).where(
        Staff.id == request.staff_id, Staff.organization_id == organization.id
    ).with_for_update())
    if staff is None:
        raise HTTPException(status_code=404, detail="Staff not found.")
    verification = db_session.scalar(select(AdminVerification).where(
        AdminVerification.organization_id == organization.id,
        AdminVerification.staff_id == staff.id,
        AdminVerification.reference == request.verification_reference,
    ).with_for_update())
    if verification is None or verification.used_at is not None:
        raise HTTPException(status_code=403, detail="Verified recovery record required.")
    target_account = db_session.get(UserAccount, staff.account_id)
    if target_account is None or target_account.cognito_sub is None:
        raise HTTPException(status_code=409, detail="Staff account is unavailable.")
    cognito.set_enabled(Settings().staff_user_pool_id, target_account.cognito_sub, True)
    old_status = staff.status
    staff.status = StaffStatus.ACTIVE
    target_account.status = UserAccountStatus.ACTIVE
    db_session.add(StaffStatusHistory(
        staff_id=staff.id, executed_by_account_id=account.id,
        previous_status=old_status, new_status=StaffStatus.ACTIVE,
        reason=request.reason,
    ))
    role = db_session.scalar(select(StaffRole).where(
        StaffRole.staff_id == staff.id, StaffRole.role == StaffRoleType.ORGANIZATION_ADMIN,
        StaffRole.status == StaffRoleStatus.ACTIVE,
    ))
    if role is None:
        db_session.add(StaffRole(staff_id=staff.id, role=StaffRoleType.ORGANIZATION_ADMIN))
    verification.used_at = datetime.now(timezone.utc)
    db_session.add(SystemAdminAudit(
        account_id=account.id, action="recover_admin", target_id=staff.id,
        reference=request.verification_reference,
    ))
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()
        if old_status != StaffStatus.ACTIVE:
            cognito.set_enabled(Settings().staff_user_pool_id, target_account.cognito_sub, False)
        raise
    return {"id": staff.id, "status": staff.status}


@router.get("/system-admin/reservations")
def investigate_reservations(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    organization_id: UUID,
    case_reference: Annotated[str, Query(min_length=1, max_length=128)],
    reservation_id: UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> dict:
    account, _ = require_system_admin(current_user, db_session)
    if reservation_id is None and (from_date is None or to_date is None):
        raise HTTPException(status_code=422, detail="Reservation ID or date range required.")
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="Invalid date range.")
    query = select(Reservation).join(Store, Store.id == Reservation.store_id).where(
        Store.organization_id == organization_id,
    )
    if reservation_id is not None:
        query = query.where(Reservation.id == reservation_id)
    japan = ZoneInfo("Asia/Tokyo")
    if from_date is not None:
        query = query.where(Reservation.starts_at >= datetime.combine(from_date, datetime.min.time(), japan).astimezone(timezone.utc))
    if to_date is not None:
        query = query.where(Reservation.starts_at < datetime.combine(to_date + timedelta(days=1), datetime.min.time(), japan).astimezone(timezone.utc))
    if cursor is not None:
        query = query.where(Reservation.id > cursor)
    reservations = db_session.scalars(query.order_by(Reservation.id).limit(limit + 1)).all()
    for reservation in reservations[:limit]:
        db_session.add(SystemAdminAudit(
            account_id=account.id, action="reservation_inquiry", target_id=reservation.id,
            reference=case_reference,
        ))
    db_session.commit()
    return {
        "items": [{"id": item.id, "status": item.status, "starts_at": item.starts_at,
                   "ends_at": item.ends_at, "store_id": item.store_id} for item in reservations[:limit]],
        "next_cursor": reservations[limit - 1].id if len(reservations) > limit else None,
    }
