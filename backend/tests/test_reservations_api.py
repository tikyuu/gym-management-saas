from datetime import datetime, time, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
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
from app.models.catalog import Menu, MenuStatus, Plan, PlanUsageType, StoreMenu, TrainerMenu
from app.models.contract import Contract, ContractStatus
from app.models.member import Member
from app.models.organization import Organization, OrganizationStatus
from app.models.reservation import (
    Reservation,
    ReservationStatus,
    ReservationStatusHistory,
    UsageEntry,
    UsageEntryType,
)
from app.models.scheduling import UnavailablePeriod, WorkShift
from app.models.staff import Staff, StaffRole, StaffRoleType, StaffStatus, StaffStoreMembership
from app.models.store import Store, StoreRegularHour, StoreSpecialDay, StoreSpecialDayHour, StoreStatus
from app.models.user_account import UserAccount


JAPAN_TIMEZONE = ZoneInfo("Asia/Tokyo")
BOOKING_DATE = datetime(2030, 10, 10, tzinfo=JAPAN_TIMEZONE).date()


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kwargs):
    return "JSON"


@pytest.fixture
def booking_environment():
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
        Plan.__table__,
        Contract.__table__,
        Staff.__table__,
        StaffStoreMembership.__table__,
        StaffRole.__table__,
        TrainerMenu.__table__,
        WorkShift.__table__,
        UnavailablePeriod.__table__,
        Reservation.__table__,
        ReservationStatusHistory.__table__,
        UsageEntry.__table__,
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
    user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer")

    with Session(engine) as session:
        account = UserAccount(user_pool_id=user.user_pool_id, cognito_sub=user.cognito_sub)
        staff_account = UserAccount(user_pool_id="staff", cognito_sub=str(uuid4()))
        organization = Organization(name="サンプルジム", status=OrganizationStatus.ACTIVE)
        session.add_all([account, staff_account, organization])
        session.flush()
        member = Member(
            account_id=account.id,
            organization_id=organization.id,
            member_number="M0001",
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
            free_cancellation_hours=24,
        )
        menu = Menu(
            organization_id=organization.id,
            name="トレーニング60分",
            duration_minutes=60,
            status=MenuStatus.ACTIVE,
        )
        plan = Plan(
            organization_id=organization.id,
            name="月2回",
            usage_type=PlanUsageType.LIMITED,
            usage_limit=2,
            period_type="fixed",
            period_months=1,
            price_yen=10000,
            status="active",
        )
        staff = Staff(
            account_id=staff_account.id,
            organization_id=organization.id,
            name="山田 花子",
            status=StaffStatus.ACTIVE,
        )
        session.add_all([member, store, menu, plan, staff])
        session.flush()
        membership = StaffStoreMembership(staff_id=staff.id, store_id=store.id)
        session.add(membership)
        session.flush()
        contract = Contract(
            member_id=member.id,
            plan_id=plan.id,
            plan_snapshot={
                "store_ids": [str(store.id)],
                "menu_ids": [str(menu.id)],
                "usage_type": "limited",
            },
            status=ContractStatus.ACTIVE,
            starts_on=BOOKING_DATE - timedelta(days=10),
            ends_on=BOOKING_DATE + timedelta(days=10),
        )
        session.add_all(
            [
                StoreMenu(store_id=store.id, menu_id=menu.id),
                StoreRegularHour(
                    store_id=store.id,
                    day_of_week=BOOKING_DATE.isoweekday(),
                    opens_at=time(9),
                    closes_at=time(12),
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
                    starts_at=datetime(2030, 10, 10, 9, tzinfo=JAPAN_TIMEZONE).astimezone(timezone.utc),
                    ends_at=datetime(2030, 10, 10, 12, tzinfo=JAPAN_TIMEZONE).astimezone(timezone.utc),
                ),
                contract,
            ]
        )
        session.flush()
        session.add(
            UsageEntry(
                contract_id=contract.id,
                entry_type=UsageEntryType.GRANT,
                available_usage_delta=2,
                reserved_usage_delta=0,
                consumed_usage_delta=0,
                usage_period_starts_on=contract.starts_on,
                usage_period_ends_on=contract.ends_on,
            )
        )
        session.commit()
        identifiers = {
            "store_id": store.id,
            "menu_id": menu.id,
            "trainer_id": staff.id,
            "member_id": member.id,
            "contract_id": contract.id,
        }

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db_session] = get_test_session
    try:
        with TestClient(app) as client:
            yield client, engine, identifiers
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def booking_request(identifiers: dict[str, UUID], hour: int = 9) -> dict[str, str]:
    return {
        "store_id": str(identifiers["store_id"]),
        "menu_id": str(identifiers["menu_id"]),
        "starts_at": datetime(2030, 10, 10, hour, tzinfo=JAPAN_TIMEZONE).isoformat(),
    }


def test_create_reservation_holds_usage_and_prevents_overlap(booking_environment) -> None:
    client, engine, identifiers = booking_environment
    response = client.post("/api/v1/reservations", json=booking_request(identifiers))
    assert response.status_code == 201
    assert response.json()["status"] == "confirmed"
    assert response.json()["trainer"]["id"] == str(identifiers["trainer_id"])
    assert response.json()["ends_at"].startswith("2030-10-10T10:00:00")
    assert client.post("/api/v1/reservations", json=booking_request(identifiers)).status_code == 409
    with Session(engine) as session:
        assert len(session.scalars(select(Reservation)).all()) == 1
        hold = session.scalars(select(UsageEntry).where(UsageEntry.entry_type == UsageEntryType.HOLD)).one()
        assert (hold.available_usage_delta, hold.reserved_usage_delta) == (-1, 1)
        assert hold.reservation_id == UUID(response.json()["id"])


def test_create_reservation_rejects_invalid_slot_and_exhausted_usage(booking_environment) -> None:
    client, engine, identifiers = booking_environment
    request = booking_request(identifiers)
    assert client.post("/api/v1/reservations", json={**request, "starts_at": "2030-10-10T09:00:00"}).status_code == 422
    assert client.post("/api/v1/reservations", json={**request, "trainer_id": str(uuid4())}).status_code == 404
    assert client.post("/api/v1/reservations", json={**request, "starts_at": "2030-10-10T09:15:00+09:00"}).status_code == 409
    with Session(engine) as session:
        grant = session.scalars(select(UsageEntry)).one()
        grant.available_usage_delta = 0
        session.commit()
    assert client.post("/api/v1/reservations", json=request).status_code == 409
    with Session(engine) as session:
        assert not session.scalars(select(Reservation)).all()


def test_list_detail_and_cancel_keep_history_and_release_usage(booking_environment) -> None:
    client, engine, identifiers = booking_environment
    first = client.post("/api/v1/reservations", json=booking_request(identifiers, 9))
    second = client.post("/api/v1/reservations", json=booking_request(identifiers, 10))
    assert first.status_code == second.status_code == 201
    reservation_id = first.json()["id"]

    first_page = client.get("/api/v1/members/me/reservations", params={"limit": 1}).json()
    assert [item["id"] for item in first_page["items"]] == [reservation_id]
    second_page = client.get(
        "/api/v1/members/me/reservations",
        params={"limit": 1, "cursor": first_page["next_cursor"]},
    ).json()
    assert [item["id"] for item in second_page["items"]] == [second.json()["id"]]
    assert second_page["next_cursor"] is None
    assert client.get("/api/v1/members/me/reservations", params={"cursor": "bad"}).status_code == 422

    detail = client.get(f"/api/v1/members/me/reservations/{reservation_id}").json()
    assert detail["can_cancel"] is True
    assert detail["free_cancellation_until"].startswith("2030-10-09T09:00:00")
    cancelled = client.post(
        f"/api/v1/reservations/{reservation_id}/cancel", json={"reason": "予定変更"}
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["usage_result"] == "returned"
    assert client.post(f"/api/v1/reservations/{reservation_id}/cancel", json={}).status_code == 409
    assert client.get("/api/v1/members/me/reservations", params={"scope": "past"}).json()["items"][0]["id"] == reservation_id
    assert client.post("/api/v1/reservations", json=booking_request(identifiers, 9)).status_code == 201

    with Session(engine) as session:
        histories = session.scalars(select(ReservationStatusHistory)).all()
        release = session.scalars(select(UsageEntry).where(UsageEntry.entry_type == UsageEntryType.RELEASE)).one()
        assert len(histories) == 1 and histories[0].reason == "予定変更"
        assert (release.available_usage_delta, release.reserved_usage_delta) == (1, -1)
        assert session.get(Reservation, UUID(reservation_id)).status == ReservationStatus.CANCELLED


def test_late_cancellation_consumes_usage(booking_environment, monkeypatch) -> None:
    client, engine, identifiers = booking_environment
    response = client.post("/api/v1/reservations", json=booking_request(identifiers))
    reservation_id = response.json()["id"]

    class LateCancellationTime(datetime):
        @classmethod
        def now(cls, tz=None):
            simulated = datetime(2030, 10, 9, 12, tzinfo=JAPAN_TIMEZONE)
            return simulated.astimezone(tz) if tz else simulated.replace(tzinfo=None)

    monkeypatch.setattr("app.api.v1.reservations.datetime", LateCancellationTime)
    cancelled = client.post(f"/api/v1/reservations/{reservation_id}/cancel", json={})
    assert cancelled.status_code == 200
    assert cancelled.json()["usage_result"] == "consumed"
    with Session(engine) as session:
        consume = session.scalars(select(UsageEntry).where(UsageEntry.entry_type == UsageEntryType.CONSUME)).one()
        assert (consume.reserved_usage_delta, consume.consumed_usage_delta) == (-1, 1)


def test_unlimited_contract_does_not_write_usage_entries(booking_environment) -> None:
    client, engine, identifiers = booking_environment
    with Session(engine) as session:
        contract = session.get(Contract, identifiers["contract_id"])
        contract.plan_snapshot = {**contract.plan_snapshot, "usage_type": "unlimited"}
        session.query(UsageEntry).delete()
        session.commit()
    response = client.post("/api/v1/reservations", json=booking_request(identifiers))
    assert response.status_code == 201
    cancelled = client.post(f"/api/v1/reservations/{response.json()['id']}/cancel", json={})
    assert cancelled.status_code == 200
    assert cancelled.json()["usage_result"] == "not_applicable"
    with Session(engine) as session:
        assert not session.scalars(select(UsageEntry)).all()


def test_other_member_cannot_read_or_cancel_reservation(booking_environment) -> None:
    client, engine, identifiers = booking_environment
    response = client.post("/api/v1/reservations", json=booking_request(identifiers))
    reservation_id = response.json()["id"]
    another_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer")
    with Session(engine) as session:
        account = UserAccount(user_pool_id="customer", cognito_sub=another_user.cognito_sub)
        session.add(account)
        session.flush()
        original = session.get(Member, identifiers["member_id"])
        session.add(
            Member(
                account_id=account.id,
                organization_id=original.organization_id,
                member_number="M0002",
                name="佐藤 次郎",
                name_kana="サトウ ジロウ",
                phone_number="09012345679",
            )
        )
        session.commit()
    app.dependency_overrides[get_current_user] = lambda: another_user
    assert client.get("/api/v1/members/me/reservations").json()["items"] == []
    assert client.get(f"/api/v1/members/me/reservations/{reservation_id}").status_code == 404
    assert client.post(f"/api/v1/reservations/{reservation_id}/cancel", json={}).status_code == 404
