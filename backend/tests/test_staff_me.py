from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.main import app
from app.models.base import Base
from app.models.member import Member
from app.models.organization import Organization
from app.models.staff import (
    Staff,
    StaffRole,
    StaffRoleStatus,
    StaffRoleType,
    StaffStatus,
    StaffStoreMembership,
    StaffStoreMembershipStatus,
)
from app.models.store import Store
from app.models.user_account import UserAccount, UserAccountStatus


def test_staff_me_returns_only_active_roles_and_memberships() -> None:
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
            Staff.__table__,
            Store.__table__,
            StaffStoreMembership.__table__,
            StaffRole.__table__,
        ],
    )
    current_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    with Session(engine) as session:
        account = UserAccount(
            user_pool_id=current_user.user_pool_id,
            cognito_sub=current_user.cognito_sub,
        )
        organization = Organization(name="サンプルジム")
        session.add_all([account, organization])
        session.flush()
        staff = Staff(
            account_id=account.id,
            organization_id=organization.id,
            name="山田 花子",
            status=StaffStatus.ACTIVE,
        )
        active_store = Store(
            organization_id=organization.id,
            name="渋谷店",
            address="東京都渋谷区",
            phone_number="0312345678",
        )
        session.add_all([staff, active_store])
        session.flush()
        active_membership = StaffStoreMembership(
            staff_id=staff.id,
            store_id=active_store.id,
        )
        session.add(active_membership)
        session.flush()
        session.add_all(
            [
                StaffRole(staff_id=staff.id, role=StaffRoleType.ORGANIZATION_ADMIN),
                StaffRole(
                    staff_id=staff.id,
                    store_membership_id=active_membership.id,
                    role=StaffRoleType.TRAINER,
                ),
                StaffRole(
                    staff_id=staff.id,
                    store_membership_id=active_membership.id,
                    role=StaffRoleType.STORE_ADMIN,
                    status=StaffRoleStatus.INACTIVE,
                    revoked_at=datetime.now(timezone.utc),
                ),
            ]
        )
        session.commit()
        staff_id = staff.id
        account_id = account.id
        active_store_id = active_store.id
        active_membership_id = active_membership.id

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/me")
            assert response.status_code == 200
            assert response.json() == {
                "user_type": "staff",
                "display_name": "山田 花子",
                "roles": [
                    {"role": "organization_admin"},
                    {"role": "trainer", "store_id": str(active_store_id)},
                ],
            }

            with Session(engine) as session:
                membership = session.get(StaffStoreMembership, active_membership_id)
                membership.status = StaffStoreMembershipStatus.INACTIVE
                membership.ended_at = datetime.now(timezone.utc)
                session.commit()
            assert client.get("/api/v1/me").json()["roles"] == [
                {"role": "organization_admin"}
            ]

            with Session(engine) as session:
                session.get(Staff, staff_id).status = StaffStatus.INACTIVE
                session.commit()
            assert client.get("/api/v1/me").status_code == 403

            with Session(engine) as session:
                session.get(Staff, staff_id).status = StaffStatus.ACTIVE
                session.get(UserAccount, account_id).status = UserAccountStatus.DISABLED
                session.commit()
            assert client.get("/api/v1/me").status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
