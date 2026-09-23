from datetime import date, datetime, time, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.main import app
from app.models.base import Base
from app.models.catalog import Menu, MenuStatus, StoreMenu, TrainerMenu
from app.models.contract import Contract, ContractStatus
from app.models.member import Member
from app.models.organization import Organization, OrganizationStatus
from app.models.reservation import Reservation
from app.models.scheduling import (
    UnavailablePeriod,
    UnavailablePeriodReason,
    WorkShift,
)
from app.models.staff import (
    Staff,
    StaffRole,
    StaffRoleType,
    StaffStatus,
    StaffStoreMembership,
)
from app.models.store import (
    Store,
    StoreRegularHour,
    StoreSpecialDay,
    StoreSpecialDayHour,
    StoreStatus,
)
from app.models.user_account import UserAccount


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kwargs):
    return "JSON"


def utc_time(hour: int) -> datetime:
    return datetime(2030, 10, 10, hour, tzinfo=ZoneInfo("Asia/Tokyo")).astimezone(
        timezone.utc
    )


def test_availability_endpoint_checks_booking_conditions() -> None:
    tables = [
        UserAccount.__table__,
        Organization.__table__,
        Member.__table__,
        Store.__table__,
        StoreRegularHour.__table__,
        StoreSpecialDay.__table__,
        StoreSpecialDayHour.__table__,
        Menu.__table__,
        StoreMenu.__table__,
        Contract.__table__,
        Staff.__table__,
        StaffStoreMembership.__table__,
        StaffRole.__table__,
        TrainerMenu.__table__,
        WorkShift.__table__,
        UnavailablePeriod.__table__,
        Reservation.__table__,
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
    customer = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer")
    other_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    target_date = date(2030, 10, 10)

    with Session(engine) as session:
        account = UserAccount(user_pool_id="customer", cognito_sub=customer.cognito_sub)
        other_account = UserAccount(user_pool_id="staff", cognito_sub=other_user.cognito_sub)
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
        store = Store(
            organization_id=organization.id,
            name="渋谷店",
            address="東京都渋谷区",
            phone_number="0312345678",
            status=StoreStatus.ACTIVE,
            booking_interval_minutes=30,
        )
        menu = Menu(
            organization_id=organization.id,
            name="トレーニング60分",
            duration_minutes=60,
            status=MenuStatus.ACTIVE,
        )
        staff = Staff(
            account_id=other_account.id,
            organization_id=organization.id,
            name="山田 花子",
            status=StaffStatus.ACTIVE,
        )
        session.add_all([member, store, menu, staff])
        session.flush()
        membership = StaffStoreMembership(staff_id=staff.id, store_id=store.id)
        session.add(membership)
        session.flush()
        session.add_all(
            [
                StoreRegularHour(
                    store_id=store.id,
                    day_of_week=target_date.isoweekday(),
                    opens_at=time(9),
                    closes_at=time(12),
                ),
                StoreMenu(store_id=store.id, menu_id=menu.id),
                Contract(
                    member_id=member.id,
                    plan_id=uuid4(),
                    plan_snapshot={
                        "store_ids": [str(store.id)],
                        "menu_ids": [str(menu.id)],
                    },
                    status=ContractStatus.SCHEDULED,
                    starts_on=date(2030, 10, 1),
                    ends_on=date(2030, 10, 31),
                ),
                StaffRole(
                    staff_id=staff.id,
                    store_membership_id=membership.id,
                    role=StaffRoleType.TRAINER,
                ),
                TrainerMenu(staff_store_membership_id=membership.id, menu_id=menu.id),
                WorkShift(
                    staff_id=staff.id,
                    staff_store_membership_id=membership.id,
                    starts_at=utc_time(9),
                    ends_at=utc_time(12),
                ),
            ]
        )
        session.commit()
        store_id = store.id
        menu_id = menu.id
        staff_id = staff.id
        member_id = member.id
        membership_id = membership.id

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = get_test_session
    app.dependency_overrides[get_current_user] = lambda: customer
    try:
        with TestClient(app) as client:
            path = f"/api/v1/stores/{store_id}/availability"
            parameters = {"date": target_date.isoformat(), "menu_id": str(menu_id)}
            response = client.get(path, params=parameters)
            assert response.status_code == 200
            assert [slot["starts_at"][11:16] for slot in response.json()["slots"]] == [
                "09:00", "09:30", "10:00", "10:30", "11:00"
            ]
            assert client.get(
                path, params={**parameters, "trainer_id": str(staff_id)}
            ).status_code == 200
            assert client.get(
                path, params={**parameters, "trainer_id": str(uuid4())}
            ).status_code == 404
            assert client.get(
                path, params={"date": "2030-11-01", "menu_id": str(menu_id)}
            ).status_code == 404

            with Session(engine) as session:
                shift = session.scalars(select(WorkShift)).one()
                session.add(
                    UnavailablePeriod(
                        work_shift_id=shift.id,
                        starts_at=utc_time(10),
                        ends_at=utc_time(11),
                        reason=UnavailablePeriodReason.BREAK,
                    )
                )
                session.commit()
            assert [
                slot["starts_at"][11:16]
                for slot in client.get(path, params=parameters).json()["slots"]
            ] == [
                "09:00", "11:00"
            ]

            with Session(engine) as session:
                contract = session.scalars(select(Contract)).one()
                session.add(
                    Reservation(
                        member_id=member_id,
                        contract_id=contract.id,
                        store_id=store_id,
                        staff_id=staff_id,
                        staff_store_membership_id=membership_id,
                        menu_id=menu_id,
                        reservation_snapshot={},
                        starts_at=utc_time(9),
                        ends_at=utc_time(10),
                    )
                )
                session.commit()
            assert [
                slot["starts_at"][11:16]
                for slot in client.get(path, params=parameters).json()["slots"]
            ] == [
                "11:00"
            ]

            with Session(engine) as session:
                session.add(
                    StoreSpecialDay(
                        store_id=store_id,
                        business_date=target_date,
                        is_closed=True,
                    )
                )
                session.commit()
            assert client.get(path, params=parameters).json()["slots"] == []

            app.dependency_overrides[get_current_user] = lambda: other_user
            assert client.get(path, params=parameters).status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
