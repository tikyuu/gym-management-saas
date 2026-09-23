from datetime import date, time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.main import app
from app.models.base import Base
from app.models.contract import Contract
from app.models.organization import Organization
from app.models.reservation import Reservation
from app.models.staff import Staff, StaffRole, StaffRoleType, StaffStatus, StaffStoreMembership
from app.models.store import Store, StoreRegularHour, StoreSpecialDay, StoreSpecialDayHour
from app.models.user_account import UserAccount


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kwargs):
    return "JSON"


def test_store_management_is_scoped_and_validated() -> None:
    tables = [
        UserAccount.__table__, Organization.__table__, Staff.__table__,
        StaffRole.__table__, StaffStoreMembership.__table__, Store.__table__,
        StoreRegularHour.__table__, StoreSpecialDay.__table__,
        StoreSpecialDayHour.__table__,
        Contract.__table__, Reservation.__table__,
    ]
    for table in tables:
        for constraint in table.constraints:
            if isinstance(constraint, ExcludeConstraint):
                constraint.ddl_if(dialect="postgresql")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=tables)
    admin_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    outsider = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    with Session(engine) as session:
        organization = Organization(name="運営事業者")
        other_organization = Organization(name="別事業者")
        account = UserAccount(user_pool_id="staff", cognito_sub=admin_user.cognito_sub)
        other_account = UserAccount(user_pool_id="staff", cognito_sub=outsider.cognito_sub)
        session.add_all([organization, other_organization, account, other_account])
        session.flush()
        admin = Staff(organization_id=organization.id, account_id=account.id, name="管理者", status=StaffStatus.ACTIVE)
        other_admin = Staff(organization_id=other_organization.id, account_id=other_account.id, name="別管理者", status=StaffStatus.ACTIVE)
        session.add_all([admin, other_admin])
        session.flush()
        session.add_all([
            StaffRole(staff_id=admin.id, role=StaffRoleType.ORGANIZATION_ADMIN),
            StaffRole(staff_id=other_admin.id, role=StaffRoleType.ORGANIZATION_ADMIN),
        ])
        session.commit()

    def test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/management/stores",
                json={"name": "渋谷店", "address": "東京都", "phone_number": "0312345678"},
            )
            assert created.status_code == 201
            store_id = created.json()["id"]
            assert created.json()["status"] == "draft"
            listed = client.get("/api/v1/management/stores")
            assert listed.status_code == 200
            assert [item["id"] for item in listed.json()["items"]] == [store_id]
            assert client.patch(f"/api/v1/management/stores/{store_id}", json={"booking_interval_minutes": 12}).status_code == 422
            assert client.patch(f"/api/v1/management/stores/{store_id}/status", json={"status": "closed", "reason": "閉店"}).status_code == 409
            assert client.put(
                f"/api/v1/management/stores/{store_id}/regular-hours",
                json={"hours": [
                    {"day_of_week": 1, "opens_at": "09:00", "closes_at": "12:00"},
                    {"day_of_week": 1, "opens_at": "11:00", "closes_at": "13:00"},
                ]},
            ).status_code == 422
            assert client.put(
                f"/api/v1/management/stores/{store_id}/regular-hours",
                json={"hours": [{"day_of_week": 1, "opens_at": "09:00", "closes_at": "12:00"}]},
            ).status_code == 200
            assert client.put(
                f"/api/v1/management/stores/{store_id}/special-days/2030-10-10",
                json={"is_closed": True, "reason": "祝日", "hours": []},
            ).status_code == 200
            assert client.get(f"/api/v1/management/stores/{store_id}").json()["special_days"][0]["is_closed"] is True
            app.dependency_overrides[get_current_user] = lambda: outsider
            assert client.get(f"/api/v1/management/stores/{store_id}").status_code == 404
            assert client.get("/api/v1/management/stores").json()["items"] == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
