from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.main import app
from app.models.base import Base
from app.models.catalog import Menu, MenuStatus, StoreMenu
from app.models.contract import Contract, ContractStatus
from app.models.member import Member, MemberStatus
from app.models.organization import Organization, OrganizationStatus
from app.models.store import Store, StoreStatus
from app.models.user_account import UserAccount


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kwargs):
    return "JSON"


def test_booking_catalog_respects_each_contract_snapshot() -> None:
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
            Store.__table__,
            Menu.__table__,
            StoreMenu.__table__,
            Contract.__table__,
        ],
    )
    current_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer")
    other_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()

    with Session(engine) as session:
        account = UserAccount(
            user_pool_id=current_user.user_pool_id,
            cognito_sub=current_user.cognito_sub,
        )
        other_account = UserAccount(
            user_pool_id=other_user.user_pool_id,
            cognito_sub=other_user.cognito_sub,
        )
        organization = Organization(name="サンプルジム", status=OrganizationStatus.ACTIVE)
        session.add_all([account, other_account, organization])
        session.flush()
        member = Member(
            account_id=account.id,
            organization_id=organization.id,
            member_number="M000001",
            name="山田 太郎",
            name_kana="ヤマダ タロウ",
            phone_number="09012345678",
        )
        first_store = Store(
            organization_id=organization.id,
            name="渋谷店",
            address="東京都渋谷区",
            phone_number="0312345678",
            status=StoreStatus.ACTIVE,
        )
        second_store = Store(
            organization_id=organization.id,
            name="新宿店",
            address="東京都新宿区",
            phone_number="0312345679",
            status=StoreStatus.ACTIVE,
        )
        first_menu = Menu(
            organization_id=organization.id,
            name="トレーニング60分",
            duration_minutes=60,
            status=MenuStatus.ACTIVE,
        )
        second_menu = Menu(
            organization_id=organization.id,
            name="トレーニング30分",
            duration_minutes=30,
            status=MenuStatus.ACTIVE,
        )
        session.add_all([member, first_store, second_store, first_menu, second_menu])
        session.flush()
        session.add_all(
            [
                StoreMenu(store_id=first_store.id, menu_id=first_menu.id),
                StoreMenu(store_id=first_store.id, menu_id=second_menu.id),
                StoreMenu(store_id=second_store.id, menu_id=second_menu.id),
                Contract(
                    member_id=member.id,
                    plan_id=uuid4(),
                    plan_snapshot={
                        "store_ids": [str(first_store.id)],
                        "menu_ids": [str(first_menu.id)],
                    },
                    status=ContractStatus.ACTIVE,
                    starts_on=today - timedelta(days=5),
                    ends_on=today + timedelta(days=5),
                ),
                Contract(
                    member_id=member.id,
                    plan_id=uuid4(),
                    plan_snapshot={
                        "store_ids": [str(second_store.id)],
                        "menu_ids": [str(second_menu.id)],
                    },
                    status=ContractStatus.SCHEDULED,
                    starts_on=today + timedelta(days=6),
                    ends_on=today + timedelta(days=20),
                ),
            ]
        )
        session.commit()
        member_id = member.id
        first_store_id = first_store.id
        second_store_id = second_store.id
        first_menu_id = first_menu.id

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    try:
        with TestClient(app) as client:
            stores_response = client.get("/api/v1/stores")
            assert stores_response.status_code == 200
            assert {store["id"] for store in stores_response.json()} == {
                str(first_store_id),
                str(second_store_id),
            }

            first_menus = client.get(f"/api/v1/stores/{first_store_id}/menus")
            assert first_menus.status_code == 200
            assert [menu["id"] for menu in first_menus.json()] == [str(first_menu_id)]
            assert client.get(f"/api/v1/stores/{uuid4()}/menus").status_code == 404

            with Session(engine) as session:
                session.get(Menu, first_menu_id).status = MenuStatus.INACTIVE
                session.commit()
            assert client.get(f"/api/v1/stores/{first_store_id}/menus").json() == []

            with Session(engine) as session:
                session.get(Store, first_store_id).status = StoreStatus.SUSPENDED
                session.commit()
            assert client.get(f"/api/v1/stores/{first_store_id}/menus").status_code == 404
            assert [store["id"] for store in client.get("/api/v1/stores").json()] == [
                str(second_store_id)
            ]

            app.dependency_overrides[get_current_user] = lambda: other_user
            assert client.get("/api/v1/stores").status_code == 403
            app.dependency_overrides[get_current_user] = lambda: current_user

            with Session(engine) as session:
                session.get(Member, member_id).status = MemberStatus.SUSPENDED
                session.commit()
            assert client.get("/api/v1/stores").json() == []
            assert client.get(f"/api/v1/stores/{first_store_id}/menus").status_code == 404
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
