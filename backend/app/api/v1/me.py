from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.member import Member
from app.models.user_account import UserAccount, UserAccountStatus


router = APIRouter()


class CurrentUserResponse(BaseModel):
    cognito_sub: str
    user_pool_id: str


class MemberCurrentUserResponse(BaseModel):
    user_type: Literal["member"] = "member"
    display_name: str


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


@router.get("/me", response_model=CurrentUserResponse | MemberCurrentUserResponse)
def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> CurrentUserResponse | MemberCurrentUserResponse:
    account = get_active_account(current_user, db_session)
    member = db_session.scalar(select(Member).where(Member.account_id == account.id))
    if member is not None:
        return MemberCurrentUserResponse(display_name=member.name)

    return CurrentUserResponse(
        cognito_sub=current_user.cognito_sub,
        user_pool_id=current_user.user_pool_id,
    )
