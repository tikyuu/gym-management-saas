from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.user_account import UserAccount, UserAccountStatus


router = APIRouter()


class CurrentUserResponse(BaseModel):
    cognito_sub: str
    user_pool_id: str


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> CurrentUserResponse:
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

    return CurrentUserResponse(
        cognito_sub=current_user.cognito_sub,
        user_pool_id=current_user.user_pool_id,
    )
