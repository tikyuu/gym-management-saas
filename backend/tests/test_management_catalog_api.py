from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.main import app
from app.models.base import Base
from app.models.catalog import Menu, Plan, PlanMenu, PlanStore, StoreMenu, TrainerMenu
from app.models.member import Member
from app.models.organization import Organization, OrganizationStatus
from app.models.staff import Staff, StaffRole, StaffRoleType, StaffStatus, StaffStoreMembership
from app.models.store import Store
from app.models.user_account import UserAccount


def test_catalog_management_respects_organization_scope() -> None:
    tables = [
        UserAccount.__table__, Organization.__table__, Staff.__table__,
        StaffRole.__table__, StaffStoreMembership.__table__, Member.__table__,
        Store.__table__, Menu.__table__, StoreMenu.__table__, TrainerMenu.__table__,
        Plan.__table__, PlanStore.__table__, PlanMenu.__table__,
    ]
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=tables)
    admin_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    member_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer")
    outsider_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    with Session(engine) as session:
        organization = Organization(name="事業者", status=OrganizationStatus.ACTIVE)
        other_organization = Organization(name="別事業者", status=OrganizationStatus.ACTIVE)
        accounts = [UserAccount(user_pool_id=user.user_pool_id, cognito_sub=user.cognito_sub) for user in (admin_user, member_user, outsider_user)]
        session.add_all([organization, other_organization, *accounts])
        session.flush()
        admin = Staff(organization_id=organization.id, account_id=accounts[0].id, name="管理者", status=StaffStatus.ACTIVE)
        other_admin = Staff(organization_id=other_organization.id, account_id=accounts[2].id, name="別管理者", status=StaffStatus.ACTIVE)
        member = Member(organization_id=organization.id, account_id=accounts[1].id, member_number="1", name="山田太郎", name_kana="ヤマダタロウ", phone_number="09012345678")
        store = Store(organization_id=organization.id, name="渋谷店", address="東京都", phone_number="0312345678")
        other_store = Store(organization_id=other_organization.id, name="別店舗", address="東京都", phone_number="0312345679")
        session.add_all([admin, other_admin, member, store, other_store])
        session.flush()
        session.add_all([StaffRole(staff_id=admin.id, role=StaffRoleType.ORGANIZATION_ADMIN), StaffRole(staff_id=other_admin.id, role=StaffRoleType.ORGANIZATION_ADMIN)])
        session.commit()
        store_id = store.id
        other_store_id = other_store.id

    def test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        with TestClient(app) as client:
            menu_response = client.post("/api/v1/management/menus", json={"name": "トレーニング", "duration_minutes": 60})
            assert menu_response.status_code == 201
            menu_id = menu_response.json()["id"]
            assert client.post("/api/v1/management/menus", json={"name": "トレーニング", "duration_minutes": 60}).status_code == 409
            assert client.put(f"/api/v1/management/stores/{other_store_id}/menus/{menu_id}", json={"status": "active"}).status_code == 404
            assert client.put(f"/api/v1/management/stores/{store_id}/menus/{menu_id}", json={"status": "active"}).status_code == 200
            plan_response = client.post("/api/v1/management/plans", json={
                "name": "月2回", "usage_type": "limited", "usage_limit": 2,
                "period_type": "fixed", "period_months": 1, "price_yen": 10000,
            })
            assert plan_response.status_code == 201
            plan_id = plan_response.json()["id"]
            assert client.put(f"/api/v1/management/plans/{plan_id}/stores/{store_id}", json={"status": "active"}).status_code == 200
            assert client.put(f"/api/v1/management/plans/{plan_id}/menus/{menu_id}", json={"status": "active"}).status_code == 200
            assert client.patch(f"/api/v1/management/plans/{plan_id}", json={"usage_type": "unlimited"}).status_code == 422
            assert client.patch(f"/api/v1/management/plans/{plan_id}", json={"status": "active"}).status_code == 200
            app.dependency_overrides[get_current_user] = lambda: outsider_user
            assert client.patch(f"/api/v1/management/menus/{menu_id}", json={"name": "変更"}).status_code == 404
            assert client.get("/api/v1/management/plans").json()["items"] == []
            app.dependency_overrides[get_current_user] = lambda: member_user
            assert client.get("/api/v1/plans").status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
