from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.v1.me import get_me
from app.auth.cognito import AuthenticatedUser
from app.models.base import Base
from app.models.member import Member
from app.models.user_account import UserAccount, UserAccountStatus


def test_get_me_finds_active_account_by_cognito_identity() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[UserAccount.__table__, Member.__table__])
    current_user = AuthenticatedUser(
        cognito_sub=str(uuid4()),
        user_pool_id="customer-pool",
    )

    with Session(engine) as session:
        session.add(
            UserAccount(
                user_pool_id=current_user.user_pool_id,
                cognito_sub=current_user.cognito_sub,
            )
        )
        session.commit()

        response = get_me(current_user=current_user, db_session=session)

        assert response.cognito_sub == current_user.cognito_sub
        assert response.user_pool_id == current_user.user_pool_id

        account = session.scalars(select(UserAccount)).one()
        account.status = UserAccountStatus.DISABLED
        session.commit()

        with pytest.raises(HTTPException) as disabled_error:
            get_me(current_user=current_user, db_session=session)

        assert disabled_error.value.status_code == 403

        with pytest.raises(HTTPException) as missing_error:
            get_me(
                current_user=AuthenticatedUser(
                    cognito_sub=str(uuid4()),
                    user_pool_id=current_user.user_pool_id,
                ),
                db_session=session,
            )

        assert missing_error.value.status_code == 403
