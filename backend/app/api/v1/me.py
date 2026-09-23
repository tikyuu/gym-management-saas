from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.member import Member
from app.models.staff import (
    Staff,
    StaffRole,
    StaffRoleStatus,
    StaffRoleType,
    StaffStatus,
    StaffStoreMembership,
    StaffStoreMembershipStatus,
)
from app.models.user_account import UserAccount, UserAccountStatus


router = APIRouter()


class CurrentUserResponse(BaseModel):
    cognito_sub: str
    user_pool_id: str


class MemberCurrentUserResponse(BaseModel):
    user_type: Literal["member"] = "member"
    display_name: str


class StaffRoleResponse(BaseModel):
    role: StaffRoleType
    store_id: UUID | None = None


class StaffCurrentUserResponse(BaseModel):
    user_type: Literal["staff"] = "staff"
    display_name: str
    roles: list[StaffRoleResponse]


def get_active_account(
    current_user: AuthenticatedUser,
    db_session: Session,
) -> UserAccount:
    account = db_session.scalar(
        select(UserAccount).where(
            UserAccount.user_pool_id == current_user.user_pool_id,
            UserAccount.cognito_sub == current_user.cognito_sub,
        )
    )
    if account is None or account.status != UserAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Application account is unavailable.",
        )

    return account


@router.get(
    "/me",
    response_model=CurrentUserResponse | MemberCurrentUserResponse | StaffCurrentUserResponse,
    response_model_exclude_none=True,
)
def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> CurrentUserResponse | MemberCurrentUserResponse | StaffCurrentUserResponse:
    account = get_active_account(current_user, db_session)
    member = db_session.scalar(select(Member).where(Member.account_id == account.id))
    if member is not None:
        return MemberCurrentUserResponse(display_name=member.name)

    staff = db_session.scalar(select(Staff).where(Staff.account_id == account.id))
    if staff is not None:
        if staff.status != StaffStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff profile is unavailable.",
            )

        active_roles = db_session.execute(
            select(StaffRole.role, StaffStoreMembership.store_id)
            .outerjoin(
                StaffStoreMembership,
                and_(
                    StaffStoreMembership.id == StaffRole.store_membership_id,
                    StaffStoreMembership.staff_id == staff.id,
                ),
            )
            .where(
                StaffRole.staff_id == staff.id,
                StaffRole.status == StaffRoleStatus.ACTIVE,
                or_(
                    and_(
                        StaffRole.role == StaffRoleType.ORGANIZATION_ADMIN,
                        StaffRole.store_membership_id.is_(None),
                    ),
                    StaffStoreMembership.status == StaffStoreMembershipStatus.ACTIVE,
                ),
            )
            .order_by(StaffRole.role, StaffStoreMembership.store_id)
        ).all()
        return StaffCurrentUserResponse(
            display_name=staff.name,
            roles=[
                StaffRoleResponse(role=role, store_id=store_id)
                for role, store_id in active_roles
            ],
        )

    return CurrentUserResponse(
        cognito_sub=current_user.cognito_sub,
        user_pool_id=current_user.user_pool_id,
    )
