from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.me import get_active_account
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.member import Member, MemberStatus
from app.models.organization import Organization


router = APIRouter()


class OrganizationResponse(BaseModel):
    id: UUID
    name: str


class MemberProfileResponse(BaseModel):
    id: UUID
    member_number: str
    status: MemberStatus
    name: str
    name_kana: str
    phone_number: str
    birth_date: date | None
    organization: OrganizationResponse


class MemberProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    name_kana: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, pattern=r"^0\d{9,10}$")
    birth_date: date | None = None


def get_member_profile(
    current_user: AuthenticatedUser,
    db_session: Session,
) -> tuple[Member, Organization]:
    account = get_active_account(current_user, db_session)
    profile = db_session.execute(
        select(Member, Organization)
        .join(Organization, Organization.id == Member.organization_id)
        .where(Member.account_id == account.id)
    ).one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member profile is unavailable.",
        )
    return profile


def to_response(member: Member, organization: Organization) -> MemberProfileResponse:
    return MemberProfileResponse(
        id=member.id,
        member_number=member.member_number,
        status=member.status,
        name=member.name,
        name_kana=member.name_kana,
        phone_number=member.phone_number,
        birth_date=member.birth_date,
        organization=OrganizationResponse(id=organization.id, name=organization.name),
    )


@router.get("/members/me", response_model=MemberProfileResponse)
def read_member_profile(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemberProfileResponse:
    member, organization = get_member_profile(current_user, db_session)
    return to_response(member, organization)


@router.patch("/members/me", response_model=MemberProfileResponse)
def update_member_profile(
    update: MemberProfileUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MemberProfileResponse:
    member, organization = get_member_profile(current_user, db_session)
    changes = update.model_dump(exclude_unset=True)
    if not changes or any(
        changes.get(field) is None
        for field in ("name", "name_kana", "phone_number")
        if field in changes
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one valid profile field is required.",
        )

    for field, value in changes.items():
        setattr(member, field, value)
    db_session.commit()
    return to_response(member, organization)
