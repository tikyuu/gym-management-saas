from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.cognito import AuthenticatedUser, get_current_user


router = APIRouter()


class CurrentUserResponse(BaseModel):
    cognito_sub: str
    user_pool_id: str


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        cognito_sub=current_user.cognito_sub,
        user_pool_id=current_user.user_pool_id,
    )
