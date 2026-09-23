from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.me import get_active_account
from app.auth.cognito import AuthenticatedUser
from app.models.organization import Organization, OrganizationStatus
from app.models.staff import (
    Staff,
    StaffRole,
    StaffRoleStatus,
    StaffRoleType,
    StaffStatus,
    StaffStoreMembership,
    StaffStoreMembershipStatus,
)
from app.models.user_account import UserAccount


@dataclass(frozen=True)
class StaffAccess:
    account: UserAccount
    staff: Staff
    organization: Organization
    organization_admin: bool
    managed_store_ids: frozenset[UUID]
    trainer_store_ids: frozenset[UUID]

    def require_organization_admin(self) -> None:
        if not self.organization_admin:
            raise HTTPException(status_code=403, detail="Organization administrator role required.")

    def require_store_manager(self, store_id: UUID) -> None:
        if not self.organization_admin and store_id not in self.managed_store_ids:
            raise HTTPException(status_code=404, detail="Resource not found.")

    def require_trainer(self, store_id: UUID) -> None:
        if store_id not in self.trainer_store_ids:
            raise HTTPException(status_code=404, detail="Resource not found.")


def get_staff_access(current_user: AuthenticatedUser, db_session: Session) -> StaffAccess:
    account = get_active_account(current_user, db_session)
    staff = db_session.scalar(select(Staff).where(Staff.account_id == account.id))
    if staff is None or staff.status != StaffStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Active staff profile required.")
    organization = db_session.get(Organization, staff.organization_id)
    if organization is None or organization.status == OrganizationStatus.TERMINATED:
        raise HTTPException(status_code=403, detail="Organization is unavailable.")
    rows = db_session.execute(
        select(StaffRole.role, StaffStoreMembership.store_id)
        .outerjoin(
            StaffStoreMembership,
            StaffStoreMembership.id == StaffRole.store_membership_id,
        )
        .where(
            StaffRole.staff_id == staff.id,
            StaffRole.status == StaffRoleStatus.ACTIVE,
        )
    ).all()
    active_memberships = {
        membership.store_id
        for membership in db_session.scalars(
            select(StaffStoreMembership).where(
                StaffStoreMembership.staff_id == staff.id,
                StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
            )
        )
    }
    return StaffAccess(
        account=account,
        staff=staff,
        organization=organization,
        organization_admin=any(
            role == StaffRoleType.ORGANIZATION_ADMIN and store_id is None
            for role, store_id in rows
        ),
        managed_store_ids=frozenset(
            store_id for role, store_id in rows
            if role == StaffRoleType.STORE_ADMIN and store_id in active_memberships
        ),
        trainer_store_ids=frozenset(
            store_id for role, store_id in rows
            if role == StaffRoleType.TRAINER and store_id in active_memberships
        ),
    )


def require_writable_organization(access: StaffAccess) -> None:
    if access.organization.status not in (
        OrganizationStatus.ACTIVE,
        OrganizationStatus.PREPARING,
    ):
        raise HTTPException(status_code=403, detail="Organization is not writable.")
