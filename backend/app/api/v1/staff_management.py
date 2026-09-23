from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.authorization import StaffAccess, get_staff_access, require_writable_organization
from app.api.v1.me import get_active_account
from app.api.v1.pagination import Page, page
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.reservation import Reservation, ReservationStatus
from app.models.scheduling import WorkShift, WorkShiftStatus
from app.models.staff import (
    Staff, StaffRole, StaffRoleStatus, StaffRoleType, StaffStatus,
    StaffStoreMembership, StaffStoreMembershipStatus,
)
from app.models.store import Store


router = APIRouter()


class StaffSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: StaffStatus


class StoreRole(BaseModel):
    role: StaffRoleType
    store_id: UUID | None = None


class RoleSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    roles: list[Literal[StaffRoleType.TRAINER, StaffRoleType.STORE_ADMIN]] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_roles(self):
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("roles must be unique")
        return self


class MembershipCreate(RoleSet):
    store_id: UUID


def scoped_staff(staff_id: UUID, access: StaffAccess, db_session: Session) -> Staff:
    staff = db_session.get(Staff, staff_id)
    if staff is None or staff.organization_id != access.staff.organization_id:
        raise HTTPException(status_code=404, detail="Staff not found.")
    return staff


def active_memberships(staff_id: UUID, db_session: Session) -> list[StaffStoreMembership]:
    return db_session.scalars(select(StaffStoreMembership).where(
        StaffStoreMembership.staff_id == staff_id,
        StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
    )).all()


def role_rows(staff_id: UUID, db_session: Session) -> list[StaffRole]:
    return db_session.scalars(select(StaffRole).where(
        StaffRole.staff_id == staff_id,
        StaffRole.status == StaffRoleStatus.ACTIVE,
    )).all()


def staff_detail(staff: Staff, access: StaffAccess, db_session: Session) -> dict:
    memberships = active_memberships(staff.id, db_session)
    allowed = memberships if access.organization_admin else [membership for membership in memberships if membership.store_id in access.managed_store_ids]
    roles = role_rows(staff.id, db_session)
    return {
        "id": staff.id,
        "name": staff.name,
        "status": staff.status,
        "stores": [
            {
                "id": membership.store_id,
                "name": db_session.get(Store, membership.store_id).name,
                "membership_id": membership.id,
                "roles": [role.role for role in roles if role.store_membership_id == membership.id],
            }
            for membership in allowed
        ],
        "organization_admin": access.organization_admin and any(
            role.role == StaffRoleType.ORGANIZATION_ADMIN for role in roles
        ),
    }


def require_target_manager(staff: Staff, access: StaffAccess, db_session: Session) -> None:
    if access.organization_admin:
        return
    memberships = active_memberships(staff.id, db_session)
    if not any(membership.store_id in access.managed_store_ids for membership in memberships):
        raise HTTPException(status_code=404, detail="Staff not found.")


def require_no_future_work(staff_id: UUID, db_session: Session, membership_id: UUID | None = None) -> None:
    now = datetime.now(timezone.utc)
    shifts = select(WorkShift.id).where(
        WorkShift.staff_id == staff_id,
        WorkShift.status == WorkShiftStatus.SCHEDULED,
        WorkShift.starts_at > now,
    )
    reservations = select(Reservation.id).where(
        Reservation.staff_id == staff_id,
        Reservation.status == ReservationStatus.CONFIRMED,
        Reservation.starts_at > now,
    )
    if membership_id is not None:
        shifts = shifts.where(WorkShift.staff_store_membership_id == membership_id)
        reservations = reservations.where(Reservation.staff_store_membership_id == membership_id)
    if db_session.scalar(shifts.limit(1)) is not None or db_session.scalar(reservations.limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Future shifts or reservations must be resolved first.")


@router.get("/staff/me")
def get_staff_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    memberships = active_memberships(access.staff.id, db_session)
    roles = role_rows(access.staff.id, db_session)
    return {
        "id": access.staff.id,
        "name": access.staff.name,
        "organization": {"id": access.organization.id, "name": access.organization.name},
        "roles": [
            StoreRole(role=role.role, store_id=next(
                (membership.store_id for membership in memberships if membership.id == role.store_membership_id),
                None,
            ))
            for role in roles
            if role.role == StaffRoleType.ORGANIZATION_ADMIN
            or any(membership.id == role.store_membership_id for membership in memberships)
        ],
    }


@router.post("/staff/me/activate", response_model=StaffSummary)
def activate_invited_staff(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> StaffSummary:
    account = get_active_account(current_user, db_session)
    staff = db_session.scalar(select(Staff).where(Staff.account_id == account.id))
    if staff is None:
        raise HTTPException(status_code=404, detail="Staff not found.")
    if staff.status == StaffStatus.INACTIVE:
        raise HTTPException(status_code=403, detail="Staff is inactive.")
    if staff.status == StaffStatus.INVITED:
        staff.status = StaffStatus.ACTIVE
        db_session.commit()
    return StaffSummary.model_validate(staff)


@router.get("/staff", response_model=Page[StaffSummary])
def list_staff(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    store_id: UUID | None = None,
    status: StaffStatus = StaffStatus.ACTIVE,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> Page[StaffSummary]:
    access = get_staff_access(current_user, db_session)
    if not access.organization_admin and not access.managed_store_ids:
        raise HTTPException(status_code=403, detail="Manager role required.")
    if store_id is not None and not access.organization_admin and store_id not in access.managed_store_ids:
        raise HTTPException(status_code=404, detail="Store not found.")
    query = select(Staff).where(Staff.organization_id == access.staff.organization_id, Staff.status == status)
    if store_id is not None or not access.organization_admin:
        query = query.join(StaffStoreMembership).where(StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE)
        if store_id is not None:
            query = query.where(StaffStoreMembership.store_id == store_id)
        else:
            query = query.where(StaffStoreMembership.store_id.in_(access.managed_store_ids))
        query = query.distinct()
    if cursor is not None:
        query = query.where(Staff.id > cursor)
    staff = db_session.scalars(query.order_by(Staff.id).limit(limit + 1)).all()
    return page([StaffSummary.model_validate(person) for person in staff], limit)


@router.get("/staff/{staff_id}")
def get_staff_detail(
    staff_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    staff = scoped_staff(staff_id, access, db_session)
    require_target_manager(staff, access, db_session)
    return staff_detail(staff, access, db_session)


@router.post("/staff/{staff_id}/store-memberships", status_code=201)
def add_staff_membership(
    staff_id: UUID,
    request: MembershipCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    staff = scoped_staff(staff_id, access, db_session)
    store = db_session.get(Store, request.store_id)
    if store is None or store.organization_id != access.staff.organization_id:
        raise HTTPException(status_code=404, detail="Store not found.")
    if not access.organization_admin:
        access.require_store_manager(store.id)
        if request.roles != [StaffRoleType.TRAINER] or any(role.role == StaffRoleType.ORGANIZATION_ADMIN for role in role_rows(staff.id, db_session)):
            raise HTTPException(status_code=403, detail="Role assignment not permitted.")
    if staff.status == StaffStatus.INACTIVE:
        raise HTTPException(status_code=409, detail="Staff is inactive.")
    if db_session.scalar(select(StaffStoreMembership.id).where(
        StaffStoreMembership.staff_id == staff.id,
        StaffStoreMembership.store_id == store.id,
        StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
    ).limit(1)) is not None:
        raise HTTPException(status_code=409, detail="Membership already active.")
    membership = StaffStoreMembership(staff_id=staff.id, store_id=store.id)
    db_session.add(membership)
    db_session.flush()
    db_session.add_all(StaffRole(staff_id=staff.id, store_membership_id=membership.id, role=role) for role in request.roles)
    try:
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="Membership already exists.") from error
    return {"id": membership.id, "store": {"id": store.id, "name": store.name}, "status": membership.status, "roles": request.roles}


def scoped_membership(staff_id: UUID, membership_id: UUID, access: StaffAccess, db_session: Session) -> tuple[Staff, StaffStoreMembership]:
    staff = scoped_staff(staff_id, access, db_session)
    membership = db_session.get(StaffStoreMembership, membership_id)
    if membership is None or membership.staff_id != staff.id:
        raise HTTPException(status_code=404, detail="Membership not found.")
    access.require_store_manager(membership.store_id)
    return staff, membership


@router.patch("/staff/{staff_id}/store-memberships/{membership_id}/roles")
def change_membership_roles(
    staff_id: UUID,
    membership_id: UUID,
    request: RoleSet,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    staff, membership = scoped_membership(staff_id, membership_id, access, db_session)
    if staff.status == StaffStatus.INACTIVE or membership.status != StaffStoreMembershipStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Membership is inactive.")
    existing = [role for role in role_rows(staff.id, db_session) if role.store_membership_id == membership.id]
    if not access.organization_admin and (
        StaffRoleType.STORE_ADMIN in request.roles
        or any(role.role == StaffRoleType.STORE_ADMIN for role in existing)
    ):
        raise HTTPException(status_code=403, detail="Store administrator role cannot be changed.")
    if StaffRoleType.TRAINER not in request.roles and any(role.role == StaffRoleType.TRAINER for role in existing):
        require_no_future_work(staff.id, db_session, membership.id)
    now = datetime.now(timezone.utc)
    for role in existing:
        if role.role not in request.roles:
            role.status = StaffRoleStatus.INACTIVE
            role.revoked_at = now
    for role_type in request.roles:
        if not any(role.role == role_type for role in existing):
            db_session.add(StaffRole(staff_id=staff.id, store_membership_id=membership.id, role=role_type))
    db_session.commit()
    return {"membership_id": membership.id, "roles": request.roles}


@router.post("/staff/{staff_id}/store-memberships/{membership_id}/deactivate")
def deactivate_membership(
    staff_id: UUID,
    membership_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    staff, membership = scoped_membership(staff_id, membership_id, access, db_session)
    if not access.organization_admin and any(
        role.role == StaffRoleType.STORE_ADMIN and role.store_membership_id == membership.id
        for role in role_rows(staff.id, db_session)
    ):
        raise HTTPException(status_code=403, detail="Cannot deactivate a manager membership.")
    if membership.status == StaffStoreMembershipStatus.ACTIVE:
        require_no_future_work(staff.id, db_session, membership.id)
        now = datetime.now(timezone.utc)
        membership.status = StaffStoreMembershipStatus.INACTIVE
        membership.ended_at = now
        for role in role_rows(staff.id, db_session):
            if role.store_membership_id == membership.id:
                role.status = StaffRoleStatus.INACTIVE
                role.revoked_at = now
        db_session.commit()
    return {"id": membership.id, "status": membership.status, "ended_at": membership.ended_at}


@router.post("/staff/{staff_id}/organization-admin-role")
def grant_organization_admin(
    staff_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    response: Response,
) -> dict:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    require_writable_organization(access)
    staff = scoped_staff(staff_id, access, db_session)
    if staff.status == StaffStatus.INACTIVE:
        raise HTTPException(status_code=409, detail="Staff is inactive.")
    if any(role.role == StaffRoleType.ORGANIZATION_ADMIN for role in role_rows(staff.id, db_session)):
        return {"staff_id": staff.id, "role": StaffRoleType.ORGANIZATION_ADMIN, "status": "active"}
    db_session.add(StaffRole(staff_id=staff.id, role=StaffRoleType.ORGANIZATION_ADMIN))
    db_session.commit()
    response.status_code = 201
    return {"staff_id": staff.id, "role": StaffRoleType.ORGANIZATION_ADMIN, "status": "active"}


@router.delete("/staff/{staff_id}/organization-admin-role")
def revoke_organization_admin(
    staff_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    require_writable_organization(access)
    staff = scoped_staff(staff_id, access, db_session)
    role = next((role for role in role_rows(staff.id, db_session) if role.role == StaffRoleType.ORGANIZATION_ADMIN), None)
    if role is None:
        return {"staff_id": staff.id, "role": StaffRoleType.ORGANIZATION_ADMIN, "status": "inactive"}
    active_admins = db_session.scalars(select(Staff.id).join(StaffRole, StaffRole.staff_id == Staff.id).where(
        Staff.organization_id == staff.organization_id,
        Staff.status == StaffStatus.ACTIVE,
        StaffRole.role == StaffRoleType.ORGANIZATION_ADMIN,
        StaffRole.status == StaffRoleStatus.ACTIVE,
    )).all()
    if staff.status == StaffStatus.ACTIVE and len(active_admins) <= 1:
        raise HTTPException(status_code=409, detail="The last organization administrator cannot be removed.")
    role.status = StaffRoleStatus.INACTIVE
    role.revoked_at = datetime.now(timezone.utc)
    db_session.commit()
    return {"staff_id": staff.id, "role": StaffRoleType.ORGANIZATION_ADMIN, "status": "inactive"}
