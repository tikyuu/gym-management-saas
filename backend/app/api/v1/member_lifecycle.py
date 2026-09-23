from datetime import date, datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.authorization import StaffAccess, get_staff_access, require_writable_organization
from app.api.v1.me import get_active_account
from app.api.v1.members import get_member_profile, to_response
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.contract import Contract, ContractStatus
from app.models.member import Member, MemberAuditHistory, MemberConsent, MemberStatus
from app.models.organization import Organization, OrganizationStatus
from app.models.reservation import Reservation, ReservationStatus
from app.models.store import Store
from app.models.user_account import UserAccount, UserAccountStatus
from app.services.cognito_admin import CognitoAdmin, get_cognito_admin
from app.settings import Settings


router = APIRouter()


class MemberRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    name_kana: str = Field(min_length=1, max_length=255)
    phone_number: str = Field(pattern=r"^0\d{9,10}$")
    birth_date: date | None = None
    document_version: str = Field(min_length=1, max_length=64)


class MemberCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    name_kana: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, pattern=r"^0\d{9,10}$")
    birth_date: date | None = None
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def require_change(self):
        if not set(self.model_fields_set).intersection({"name", "name_kana", "phone_number", "birth_date"}):
            raise ValueError("At least one profile field is required.")
        if any(getattr(self, field) is None for field in ("name", "name_kana", "phone_number") if field in self.model_fields_set):
            raise ValueError("Required profile fields cannot be null.")
        return self


class MemberStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: MemberStatus
    reason: str = Field(min_length=1, max_length=1000)
    emergency: bool = False


class ConfirmAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: bool


def member_scope(access: StaffAccess, db_session: Session):
    if not access.organization_admin and not access.managed_store_ids:
        raise HTTPException(status_code=403, detail="Manager role required.")
    query = select(Member).where(Member.organization_id == access.staff.organization_id)
    if not access.organization_admin:
        query = query.where(or_(
            select(Reservation.id).where(
                Reservation.member_id == Member.id,
                Reservation.store_id.in_(access.managed_store_ids),
            ).exists(),
            select(Contract.id).where(
                Contract.member_id == Member.id,
                or_(*(Contract.plan_snapshot["store_ids"].contains([str(store_id)])
                      for store_id in access.managed_store_ids)),
            ).exists(),
        ))
    return query


def scoped_member(member_id: UUID, access: StaffAccess, db_session: Session, *, lock: bool = False) -> Member:
    query = member_scope(access, db_session).where(Member.id == member_id)
    member = db_session.scalar(query.with_for_update() if lock else query)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    return member


def future_reservations(member_id: UUID, db_session: Session) -> bool:
    return db_session.scalar(select(Reservation.id).where(
        Reservation.member_id == member_id,
        Reservation.status == ReservationStatus.CONFIRMED,
        Reservation.starts_at > datetime.now(timezone.utc),
    ).limit(1)) is not None


def pending_contracts(member_id: UUID, db_session: Session) -> bool:
    return db_session.scalar(select(Contract.id).where(
        Contract.member_id == member_id,
        Contract.status.in_((ContractStatus.PENDING, ContractStatus.SCHEDULED,
                             ContractStatus.ACTIVE, ContractStatus.PAUSED)),
    ).limit(1)) is not None


def require_confirmation(request: ConfirmAction) -> None:
    if not request.confirm:
        raise HTTPException(status_code=422, detail="Confirmation is required.")


@router.post("/members/me/registration", status_code=201)
def register_member(
    request: MemberRegistration,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    cognito: Annotated[CognitoAdmin, Depends(get_cognito_admin)],
) -> dict:
    if current_user.user_pool_id != Settings().customer_user_pool_id:
        raise HTTPException(status_code=403, detail="Customer identity required.")
    cognito.verified_email(current_user.user_pool_id, current_user.cognito_sub)
    organization = db_session.get(Organization, request.organization_id)
    if organization is None or organization.status != OrganizationStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Organization is not accepting members.")
    account = db_session.scalar(select(UserAccount).where(
        UserAccount.user_pool_id == current_user.user_pool_id,
        UserAccount.cognito_sub == current_user.cognito_sub,
    ))
    if account is not None and account.status != UserAccountStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Account is unavailable.")
    if account is not None and db_session.scalar(select(Member.id).where(Member.account_id == account.id)) is not None:
        raise HTTPException(status_code=409, detail="Member is already registered.")
    if account is None:
        account = UserAccount(user_pool_id=current_user.user_pool_id, cognito_sub=current_user.cognito_sub)
        db_session.add(account)
        db_session.flush()
    member = Member(
        account_id=account.id, organization_id=organization.id,
        member_number=f"M{uuid4().hex[:12].upper()}", name=request.name,
        name_kana=request.name_kana, phone_number=request.phone_number,
        birth_date=request.birth_date,
    )
    db_session.add(member)
    db_session.flush()
    db_session.add(MemberConsent(member_id=member.id, document_version=request.document_version))
    try:
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="Member registration conflicts with an existing record.") from error
    return to_response(member, organization).model_dump()


@router.get("/management/members")
def list_members(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    cognito: Annotated[CognitoAdmin, Depends(get_cognito_admin)],
    member_number: str | None = None,
    name: str | None = None,
    name_kana: str | None = None,
    phone_number: str | None = None,
    email: EmailStr | None = None,
    status: MemberStatus | None = None,
    contract_status: ContractStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> dict:
    access = get_staff_access(current_user, db_session)
    query = member_scope(access, db_session)
    if status is None:
        query = query.where(Member.status != MemberStatus.WITHDRAWN)
    else:
        query = query.where(Member.status == status)
    for column, value in ((Member.member_number, member_number), (Member.name, name),
                          (Member.name_kana, name_kana), (Member.phone_number, phone_number)):
        if value is not None:
            query = query.where(column.ilike(f"%{value}%"))
    if contract_status is not None:
        query = query.where(select(Contract.id).where(
            Contract.member_id == Member.id, Contract.status == contract_status,
        ).exists())
    if email is not None:
        subjects = cognito.subjects_for_email(Settings().customer_user_pool_id, str(email))
        query = query.join(UserAccount, UserAccount.id == Member.account_id).where(
            UserAccount.user_pool_id == Settings().customer_user_pool_id,
            UserAccount.cognito_sub.in_(subjects),
        )
    if cursor is not None:
        query = query.where(Member.id > cursor)
    members = db_session.scalars(query.order_by(Member.id).limit(limit + 1)).all()
    return {
        "items": [{"id": member.id, "member_number": member.member_number,
                   "name": member.name, "status": member.status} for member in members[:limit]],
        "next_cursor": members[limit - 1].id if len(members) > limit else None,
    }


@router.get("/management/members/{member_id}")
def get_management_member(
    member_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    member = scoped_member(member_id, access, db_session)
    contracts = db_session.scalars(select(Contract).where(Contract.member_id == member.id)).all()
    reservation_query = select(Reservation).where(Reservation.member_id == member.id)
    if not access.organization_admin:
        reservation_query = reservation_query.where(Reservation.store_id.in_(access.managed_store_ids))
    reservations = db_session.scalars(reservation_query).all()
    return {
        **to_response(member, access.organization).model_dump(),
        "contracts": [{"id": item.id, "status": item.status} for item in contracts
                      if access.organization_admin or set(item.plan_snapshot.get("store_ids", [])).intersection(
                          str(store_id) for store_id in access.managed_store_ids
                      )],
        "reservations": [{"id": item.id, "status": item.status, "starts_at": item.starts_at}
                         for item in reservations],
    }


@router.patch("/management/members/{member_id}")
def correct_member(
    member_id: UUID,
    request: MemberCorrection,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    member = scoped_member(member_id, access, db_session, lock=True)
    changes = request.model_dump(exclude_unset=True, exclude={"reason"})
    old_values = {key: getattr(member, key) for key in changes}
    for key, value in changes.items():
        setattr(member, key, value)
    db_session.add(MemberAuditHistory(
        member_id=member.id, executed_by_account_id=access.account.id,
        action="profile_correction", reason=request.reason,
        previous_values={key: value.isoformat() if isinstance(value, date) else value
                         for key, value in old_values.items()},
        new_values={key: value.isoformat() if isinstance(value, date) else value
                    for key, value in changes.items()},
    ))
    db_session.commit()
    return to_response(member, access.organization).model_dump()


@router.patch("/management/members/{member_id}/status")
def change_member_status(
    member_id: UUID,
    request: MemberStatusChange,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    require_writable_organization(access)
    member = scoped_member(member_id, access, db_session, lock=True)
    valid = {MemberStatus.ACTIVE: MemberStatus.SUSPENDED,
             MemberStatus.SUSPENDED: MemberStatus.ACTIVE}
    if valid.get(member.status) != request.status:
        raise HTTPException(status_code=409, detail="Invalid member status transition.")
    if request.status == MemberStatus.SUSPENDED and not request.emergency and future_reservations(member.id, db_session):
        raise HTTPException(status_code=409, detail="Future reservations must be resolved first.")
    previous = member.status
    member.status = request.status
    db_session.add(MemberAuditHistory(
        member_id=member.id, executed_by_account_id=access.account.id,
        action="status_change", previous_values={"status": previous.value},
        new_values={"status": request.status.value, "emergency": request.emergency},
        reason=request.reason,
    ))
    db_session.commit()
    return {"id": member.id, "status": member.status}


@router.post("/members/me/withdraw")
def withdraw_member(
    request: ConfirmAction,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    require_confirmation(request)
    member, _ = get_member_profile(current_user, db_session)
    db_session.refresh(member, with_for_update=True)
    if member.status == MemberStatus.WITHDRAWN or pending_contracts(member.id, db_session) or future_reservations(member.id, db_session):
        raise HTTPException(status_code=409, detail="Member cannot withdraw while obligations remain.")
    old_status = member.status
    member.status = MemberStatus.WITHDRAWN
    member.withdrawn_at = datetime.now(timezone.utc)
    account = get_active_account(current_user, db_session)
    db_session.add(MemberAuditHistory(
        member_id=member.id, executed_by_account_id=account.id,
        action="withdraw", previous_values={"status": old_status.value},
        new_values={"status": member.status.value}, reason="Member confirmed withdrawal.",
    ))
    db_session.commit()
    return {"id": member.id, "status": member.status, "withdrawn_at": member.withdrawn_at}


@router.post("/members/me/rejoin")
def rejoin_member(
    request: ConfirmAction,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    require_confirmation(request)
    member, organization = get_member_profile(current_user, db_session)
    db_session.refresh(member, with_for_update=True)
    if member.status != MemberStatus.WITHDRAWN or organization.status != OrganizationStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Member cannot rejoin.")
    member.status = MemberStatus.ACTIVE
    member.withdrawn_at = None
    account = get_active_account(current_user, db_session)
    db_session.add(MemberAuditHistory(
        member_id=member.id, executed_by_account_id=account.id,
        action="rejoin", previous_values={"status": MemberStatus.WITHDRAWN.value},
        new_values={"status": MemberStatus.ACTIVE.value}, reason="Member confirmed rejoining.",
    ))
    db_session.commit()
    return {"id": member.id, "status": member.status}


@router.post("/members/me/account-deletion", status_code=202)
def request_account_deletion(
    request: ConfirmAction,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    cognito: Annotated[CognitoAdmin, Depends(get_cognito_admin)],
) -> dict:
    require_confirmation(request)
    age = datetime.now(timezone.utc) - current_user.authenticated_at if current_user.authenticated_at else None
    if age is None or not timedelta(0) <= age <= timedelta(minutes=5):
        raise HTTPException(status_code=403, detail="Recent authentication is required.")
    member, _ = get_member_profile(current_user, db_session)
    if pending_contracts(member.id, db_session) or future_reservations(member.id, db_session):
        raise HTTPException(status_code=409, detail="Outstanding obligations must be resolved first.")
    account = get_active_account(current_user, db_session)
    cognito.set_enabled(current_user.user_pool_id, current_user.cognito_sub, False)
    account.status = UserAccountStatus.DELETION_PENDING
    account.deletion_requested_at = datetime.now(timezone.utc)
    db_session.add(MemberAuditHistory(
        member_id=member.id, executed_by_account_id=account.id,
        action="account_deletion_request", reason="Member confirmed deletion request.",
    ))
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()
        cognito.set_enabled(current_user.user_pool_id, current_user.cognito_sub, True)
        raise
    return {"status": account.status, "requested_at": account.deletion_requested_at}
