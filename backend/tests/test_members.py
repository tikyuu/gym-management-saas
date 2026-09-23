from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.main import app
from app.models.base import Base
from app.models.member import Member, MemberStatus
from app.models.organization import Organization
from app.models.user_account import UserAccount, UserAccountStatus


def test_member_profile_and_current_user() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            UserAccount.__table__,
            Organization.__table__,
            Member.__table__,
        ],
    )
    current_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer")
    other_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer")

    with Session(engine) as session:
        account = UserAccount(
            user_pool_id=current_user.user_pool_id,
            cognito_sub=current_user.cognito_sub,
        )
        other_account = UserAccount(
            user_pool_id=other_user.user_pool_id,
            cognito_sub=other_user.cognito_sub,
        )
        organization = Organization(name="サンプルジム")
        session.add_all([account, other_account, organization])
        session.flush()
        account_id = account.id
        session.add(
            Member(
                account_id=account.id,
                organization_id=organization.id,
                member_number="M000001",
                name="山田 太郎",
                name_kana="ヤマダ タロウ",
                phone_number="09012345678",
                status=MemberStatus.SUSPENDED,
            )
        )
        session.commit()

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    try:
        with TestClient(app) as client:
            current_response = client.get("/api/v1/me")
            assert current_response.status_code == 200
            assert current_response.json() == {
                "user_type": "member",
                "display_name": "山田 太郎",
            }

            profile_response = client.get("/api/v1/members/me")
            assert profile_response.status_code == 200
            assert profile_response.json()["organization"]["name"] == "サンプルジム"
            assert profile_response.json()["status"] == "suspended"

            update_response = client.patch(
                "/api/v1/members/me",
                json={"name": "山田 花子", "birth_date": "1995-04-01"},
            )
            assert update_response.status_code == 200
            assert update_response.json()["name"] == "山田 花子"
            assert update_response.json()["birth_date"] == "1995-04-01"
            assert client.get("/api/v1/members/me").json()["name"] == "山田 花子"

            assert client.patch(
                "/api/v1/members/me", json={"phone_number": "invalid"}
            ).status_code == 422
            assert client.patch(
                "/api/v1/members/me", json={"name": None}
            ).status_code == 422
            assert client.patch(
                "/api/v1/members/me", json={"organization_id": str(uuid4())}
            ).status_code == 422

            app.dependency_overrides[get_current_user] = lambda: other_user
            assert client.get("/api/v1/members/me").status_code == 403
            assert client.patch(
                "/api/v1/members/me", json={"name": "不正な更新"}
            ).status_code == 403

            app.dependency_overrides[get_current_user] = lambda: current_user
            with Session(engine) as session:
                stored_account = session.get(UserAccount, account_id)
                stored_account.status = UserAccountStatus.DISABLED
                session.commit()
            assert client.get("/api/v1/members/me").status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
