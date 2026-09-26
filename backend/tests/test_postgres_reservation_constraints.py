import os
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalog import Menu, Plan, PlanPeriodType, PlanUsageType
from app.models.contract import Contract
from app.models.member import Member
from app.models.organization import Organization
from app.models.reservation import Reservation
from app.models.staff import Staff, StaffStoreMembership
from app.models.store import Store
from app.models.user_account import UserAccount


@pytest.fixture
def postgres_session():
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL constraint tests")

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            try:
                yield session
            finally:
                session.rollback()
    finally:
        engine.dispose()


def create_reservation_dependencies(session: Session):
    organization = Organization(name="予約制約テスト")
    session.add(organization)
    session.flush()

    members = [
        Member(
            organization_id=organization.id,
            member_number=f"TEST-{uuid4()}",
            name="テスト会員",
            name_kana="テストカイイン",
            phone_number="00000000000",
        )
        for _ in range(2)
    ]
    store = Store(
        organization_id=organization.id,
        name="テスト店舗",
        address="テスト住所",
        phone_number="00000000000",
    )
    menu = Menu(
        organization_id=organization.id,
        name="テストメニュー",
        duration_minutes=60,
    )
    plan = Plan(
        organization_id=organization.id,
        name="テストプラン",
        usage_type=PlanUsageType.UNLIMITED,
        period_type=PlanPeriodType.FIXED,
        period_months=1,
        price_yen=0,
    )
    accounts = [
        UserAccount(user_pool_id="test-pool", cognito_sub=str(uuid4()))
        for _ in range(2)
    ]
    session.add_all([*members, store, menu, plan, *accounts])
    session.flush()

    staff = [
        Staff(organization_id=organization.id, account_id=account.id, name="テスト担当者")
        for account in accounts
    ]
    contracts = [
        Contract(
            member_id=member.id,
            plan_id=plan.id,
            plan_snapshot={},
            starts_on=date(2030, 1, 1),
            ends_on=date(2030, 12, 31),
        )
        for member in members
    ]
    session.add_all([*staff, *contracts])
    session.flush()

    memberships = [
        StaffStoreMembership(staff_id=person.id, store_id=store.id)
        for person in staff
    ]
    session.add_all(memberships)
    session.flush()
    return members, contracts, staff, memberships, store, menu


@pytest.mark.parametrize(
    ("second_member_index", "second_staff_index", "constraint_name"),
    [
        (0, 1, "ex_reservations_member_confirmed_time"),
        (1, 0, "ex_reservations_staff_confirmed_time"),
    ],
)
def test_overlapping_confirmed_reservations_are_rejected(
    postgres_session: Session,
    second_member_index: int,
    second_staff_index: int,
    constraint_name: str,
):
    members, contracts, staff, memberships, store, menu = create_reservation_dependencies(
        postgres_session
    )

    def reservation(member_index: int, staff_index: int, start_hour: int, start_minute: int):
        return Reservation(
            member_id=members[member_index].id,
            contract_id=contracts[member_index].id,
            store_id=store.id,
            staff_id=staff[staff_index].id,
            staff_store_membership_id=memberships[staff_index].id,
            menu_id=menu.id,
            reservation_snapshot={},
            starts_at=datetime(2030, 10, 10, start_hour, start_minute, tzinfo=timezone.utc),
            ends_at=datetime(2030, 10, 10, start_hour + 1, start_minute, tzinfo=timezone.utc),
        )

    postgres_session.add(reservation(0, 0, 10, 0))
    postgres_session.flush()

    with pytest.raises(IntegrityError) as error:
        with postgres_session.begin_nested():
            postgres_session.add(reservation(second_member_index, second_staff_index, 10, 30))
            postgres_session.flush()

    assert error.value.orig.sqlstate == "23P01"
    assert error.value.orig.diag.constraint_name == constraint_name
