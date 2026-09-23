from datetime import date, datetime, time, timezone
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
from app.models.catalog import (
    Menu,
    MenuStatus,
    Plan,
    PlanMenu,
    PlanPeriodType,
    PlanStatus,
    PlanStore,
    PlanUsageType,
    StoreMenu,
    TrainerMenu,
)
from app.models.contract import Contract, ContractStatus, ContractStatusHistory
from app.models.member import Member, MemberStatus
from app.models.organization import Organization, OrganizationStatus
from app.models.reservation import Reservation, ReservationStatusHistory, UsageEntry, UsageEntryType
from app.models.scheduling import UnavailablePeriod, WorkShift
from app.models.staff import Staff, StaffRole, StaffRoleType, StaffStatus, StaffStoreMembership
from app.models.store import Store, StoreRegularHour, StoreSpecialDay, StoreSpecialDayHour, StoreStatus
from app.models.user_account import UserAccount


JAPAN_TIMEZONE = ZoneInfo("Asia/Tokyo")
START_DATE = date(2030, 10, 1)
BOOKING_TIME = datetime(2030, 10, 10, 9, tzinfo=JAPAN_TIMEZONE)


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kwargs):
    return "JSON"


@pytest.fixture
def contract_environment():
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
        PlanStore.__table__,
        PlanMenu.__table__,
        Contract.__table__,
        ContractStatusHistory.__table__,
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
    member_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer")
    admin_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    trainer_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
    other_admin_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")

    with Session(engine) as session:
        member_account = UserAccount(user_pool_id="customer", cognito_sub=member_user.cognito_sub)
        admin_account = UserAccount(user_pool_id="staff", cognito_sub=admin_user.cognito_sub)
        trainer_account = UserAccount(user_pool_id="staff", cognito_sub=trainer_user.cognito_sub)
        other_admin_account = UserAccount(user_pool_id="staff", cognito_sub=other_admin_user.cognito_sub)
        organization = Organization(name="サンプルジム", status=OrganizationStatus.ACTIVE)
        other_organization = Organization(name="別事業者", status=OrganizationStatus.ACTIVE)
        session.add_all([
            member_account, admin_account, trainer_account, other_admin_account,
            organization, other_organization,
        ])
        session.flush()
        member = Member(
            account_id=member_account.id,
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
            period_type=PlanPeriodType.FIXED,
            period_months=1,
            price_yen=10000,
            status=PlanStatus.ACTIVE,
        )
        admin = Staff(
            account_id=admin_account.id,
            organization_id=organization.id,
            name="管理者",
            status=StaffStatus.ACTIVE,
        )
        trainer = Staff(
            account_id=trainer_account.id,
            organization_id=organization.id,
            name="トレーナー",
            status=StaffStatus.ACTIVE,
        )
        other_admin = Staff(
            account_id=other_admin_account.id,
            organization_id=other_organization.id,
            name="別事業者管理者",
            status=StaffStatus.ACTIVE,
        )
        session.add_all([member, store, menu, plan, admin, trainer, other_admin])
        session.flush()
        trainer_membership = StaffStoreMembership(staff_id=trainer.id, store_id=store.id)
        session.add(trainer_membership)
        session.flush()
        session.add_all([
            PlanStore(plan_id=plan.id, store_id=store.id),
            PlanMenu(plan_id=plan.id, menu_id=menu.id),
            StoreMenu(store_id=store.id, menu_id=menu.id),
            StoreRegularHour(
                store_id=store.id,
                day_of_week=BOOKING_TIME.isoweekday(),
                opens_at=time(9),
                closes_at=time(12),
            ),
            StaffRole(staff_id=admin.id, role=StaffRoleType.ORGANIZATION_ADMIN),
            StaffRole(staff_id=other_admin.id, role=StaffRoleType.ORGANIZATION_ADMIN),
            StaffRole(
                staff_id=trainer.id,
                store_membership_id=trainer_membership.id,
                role=StaffRoleType.TRAINER,
            ),
            TrainerMenu(staff_store_membership_id=trainer_membership.id, menu_id=menu.id),
            WorkShift(
                staff_id=trainer.id,
                staff_store_membership_id=trainer_membership.id,
                starts_at=BOOKING_TIME.astimezone(timezone.utc),
                ends_at=BOOKING_TIME.replace(hour=12).astimezone(timezone.utc),
            ),
        ])
        session.commit()
        identifiers = {
            "plan_id": plan.id,
            "store_id": store.id,
            "menu_id": menu.id,
            "member_id": member.id,
            "admin_id": admin.id,
            "trainer_id": trainer.id,
            "trainer_membership_id": trainer_membership.id,
        }

    identity = {"current": member_user}

    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_current_user] = lambda: identity["current"]
    app.dependency_overrides[get_db_session] = get_test_session
    try:
        with TestClient(app) as client:
            yield client, engine, identifiers, identity, {
                "member": member_user,
                "admin": admin_user,
                "trainer": trainer_user,
                "other_admin": other_admin_user,
            }
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def apply_for_plan(client: TestClient, plan_id: UUID):
    return client.post(
        "/api/v1/members/me/contracts",
        json={"plan_id": str(plan_id), "starts_on": START_DATE.isoformat()},
    )


def test_application_approval_and_booking_share_approved_grant(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    applied = apply_for_plan(client, identifiers["plan_id"])
    assert applied.status_code == 201
    assert applied.json()["status"] == "pending"
    assert applied.json()["ends_on"] == "2030-10-31"
    contract_id = applied.json()["id"]
    assert apply_for_plan(client, identifiers["plan_id"]).status_code == 409
    assert client.post(
        "/api/v1/reservations",
        json={
            "store_id": str(identifiers["store_id"]),
            "menu_id": str(identifiers["menu_id"]),
            "starts_at": BOOKING_TIME.isoformat(),
        },
    ).status_code == 404

    with Session(engine) as session:
        plan = session.get(Plan, identifiers["plan_id"])
        plan.name = "改定後プラン"
        plan.price_yen = 20000
        plan.status = PlanStatus.INACTIVE
        session.commit()

    identity["current"] = users["admin"]
    approved = client.post(f"/api/v1/management/contracts/{contract_id}/approve", json={})
    assert approved.status_code == 200
    assert approved.json()["status"] == "scheduled"
    assert client.post(f"/api/v1/management/contracts/{contract_id}/approve", json={}).status_code == 409
    with Session(engine) as session:
        contract = session.get(Contract, UUID(contract_id))
        assert contract.plan_snapshot["store_ids"] == [str(identifiers["store_id"])]
        assert contract.plan_snapshot["menu_ids"] == [str(identifiers["menu_id"])]
        assert contract.plan_snapshot["usage_type"] == "limited"
        assert contract.plan_snapshot["name"] == "月2回"
        assert contract.plan_snapshot["price_yen"] == 10000
        history = session.scalars(select(ContractStatusHistory)).one()
        grant = session.scalars(select(UsageEntry)).one()
        assert history.new_status == ContractStatus.SCHEDULED
        assert (grant.entry_type, grant.available_usage_delta) == (UsageEntryType.GRANT, 2)
        assert grant.usage_period_starts_on == START_DATE
        assert grant.usage_period_ends_on == date(2030, 10, 31)

    identity["current"] = users["member"]
    booking = client.post(
        "/api/v1/reservations",
        json={
            "store_id": str(identifiers["store_id"]),
            "menu_id": str(identifiers["menu_id"]),
            "starts_at": BOOKING_TIME.isoformat(),
        },
    )
    assert booking.status_code == 201
    with Session(engine) as session:
        assert len(session.scalars(select(UsageEntry)).all()) == 2


def test_rejection_records_reason_and_allows_new_application(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    applied = apply_for_plan(client, identifiers["plan_id"])
    contract_id = applied.json()["id"]
    identity["current"] = users["admin"]
    assert client.post(f"/api/v1/management/contracts/{contract_id}/reject", json={}).status_code == 422
    rejected = client.post(
        f"/api/v1/management/contracts/{contract_id}/reject",
        json={"reason": "本人確認が未完了"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    with Session(engine) as session:
        assert session.scalars(select(ContractStatusHistory)).one().reason == "本人確認が未完了"
        assert not session.scalars(select(UsageEntry)).all()
    identity["current"] = users["member"]
    assert apply_for_plan(client, identifiers["plan_id"]).status_code == 201


def test_only_authorized_staff_can_approve_contract(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    applied = apply_for_plan(client, identifiers["plan_id"])
    contract_id = applied.json()["id"]
    approve_path = f"/api/v1/management/contracts/{contract_id}/approve"
    assert client.post(approve_path, json={}).status_code == 403
    identity["current"] = users["trainer"]
    assert client.post(approve_path, json={}).status_code == 403
    identity["current"] = users["other_admin"]
    assert client.post(approve_path, json={}).status_code == 404
    with Session(engine) as session:
        assert session.get(Contract, UUID(contract_id)).status == ContractStatus.PENDING


def test_store_admin_can_review_contract_for_own_store(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    applied = apply_for_plan(client, identifiers["plan_id"])
    with Session(engine) as session:
        session.add(
            StaffRole(
                staff_id=identifiers["trainer_id"],
                store_membership_id=identifiers["trainer_membership_id"],
                role=StaffRoleType.STORE_ADMIN,
            )
        )
        session.commit()
    identity["current"] = users["trainer"]
    approved = client.post(
        f"/api/v1/management/contracts/{applied.json()['id']}/approve", json={}
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "scheduled"


def test_unlimited_approval_has_no_usage_grant(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    with Session(engine) as session:
        plan = session.get(Plan, identifiers["plan_id"])
        plan.usage_type = PlanUsageType.UNLIMITED
        plan.usage_limit = None
        session.commit()
    applied = apply_for_plan(client, identifiers["plan_id"])
    assert applied.status_code == 201
    identity["current"] = users["admin"]
    approved = client.post(
        f"/api/v1/management/contracts/{applied.json()['id']}/approve", json={}
    )
    assert approved.status_code == 200
    with Session(engine) as session:
        assert not session.scalars(select(UsageEntry)).all()


def test_contract_lists_details_and_termination(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    applied = apply_for_plan(client, identifiers["plan_id"])
    assert applied.status_code == 201
    contract_id = applied.json()["id"]
    mine = client.get("/api/v1/members/me/contracts")
    assert mine.status_code == 200
    assert mine.json()["items"][0]["plan_name"] == "月2回"
    assert mine.json()["items"][0]["usage"]["available_count"] == 0
    identity["current"] = users["admin"]
    listed = client.get("/api/v1/management/contracts")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == contract_id
    assert client.get(f"/api/v1/management/contracts/{contract_id}").status_code == 200
    assert client.post(f"/api/v1/management/contracts/{contract_id}/terminate", json={"reason": "終了"}).status_code == 409
    assert client.post(f"/api/v1/management/contracts/{contract_id}/approve", json={}).status_code == 200
    terminated = client.post(f"/api/v1/management/contracts/{contract_id}/terminate", json={"reason": "終了"})
    assert terminated.status_code == 200
    assert terminated.json()["status"] == "terminated"
    with Session(engine) as session:
        history = session.scalars(select(ContractStatusHistory).where(ContractStatusHistory.contract_id == UUID(contract_id))).all()
        assert len(history) == 2
    identity["current"] = users["member"]
    assert client.get("/api/v1/members/me/contracts?scope=history").json()["items"][0]["status"] == "terminated"


def test_work_shift_and_unavailable_period_lifecycle(contract_environment) -> None:
    client, _, identifiers, identity, users = contract_environment
    identity["current"] = users["admin"]
    shift_payload = {
        "staff_id": str(identifiers["trainer_id"]),
        "store_id": str(identifiers["store_id"]),
        "starts_at": "2030-10-11T09:00:00+09:00",
        "ends_at": "2030-10-11T18:00:00+09:00",
    }
    created = client.post("/api/v1/work-shifts", json=shift_payload)
    assert created.status_code == 201
    shift_id = created.json()["id"]
    assert client.post("/api/v1/work-shifts", json=shift_payload).status_code == 409
    assert len(client.get("/api/v1/work-shifts?from=2030-10-11&to=2030-10-11").json()["items"]) == 1
    period = client.post(f"/api/v1/work-shifts/{shift_id}/unavailable-periods", json={
        "starts_at": "2030-10-11T12:00:00+09:00",
        "ends_at": "2030-10-11T13:00:00+09:00",
        "reason": "break",
    })
    assert period.status_code == 201
    assert client.delete(f"/api/v1/work-shifts/{shift_id}/unavailable-periods/{period.json()['id']}").status_code == 204
    assert client.post(f"/api/v1/work-shifts/{shift_id}/cancel").status_code == 200
    identity["current"] = users["trainer"]
    assert len(client.get("/api/v1/staff/me/work-shifts?from=2030-10-11&to=2030-10-11").json()["items"]) == 1


def test_staff_profiles_and_role_management(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    identity["current"] = users["admin"]
    assert client.get("/api/v1/staff/me").status_code == 200
    listed = client.get("/api/v1/staff")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 2
    trainer_id = identifiers["trainer_id"]
    detail = client.get(f"/api/v1/staff/{trainer_id}")
    assert detail.status_code == 200
    assert detail.json()["stores"][0]["id"] == str(identifiers["store_id"])
    granted = client.post(f"/api/v1/staff/{trainer_id}/organization-admin-role")
    assert granted.status_code == 201
    assert client.delete(f"/api/v1/staff/{trainer_id}/organization-admin-role").status_code == 200
    assert client.delete(f"/api/v1/staff/{identifiers['admin_id']}/organization-admin-role").status_code == 409
    with Session(engine) as session:
        other_store = Store(
            organization_id=session.get(Store, identifiers["store_id"]).organization_id,
            name="新宿店", address="東京都", phone_number="0312345679",
        )
        session.add(other_store)
        session.commit()
        other_store_id = other_store.id
    membership = client.post(f"/api/v1/staff/{trainer_id}/store-memberships", json={
        "store_id": str(other_store_id), "roles": ["trainer"],
    })
    assert membership.status_code == 201
    membership_id = membership.json()["id"]
    assert client.post(f"/api/v1/staff/{trainer_id}/store-memberships/{membership_id}/deactivate").status_code == 200
    identity["current"] = users["trainer"]
    assert client.get("/api/v1/staff").status_code == 403


def test_staff_reservation_scope_and_store_cancellation(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    applied = apply_for_plan(client, identifiers["plan_id"])
    identity["current"] = users["admin"]
    assert client.post(f"/api/v1/management/contracts/{applied.json()['id']}/approve", json={}).status_code == 200
    identity["current"] = users["member"]
    booking = client.post("/api/v1/reservations", json={
        "store_id": str(identifiers["store_id"]),
        "menu_id": str(identifiers["menu_id"]),
        "starts_at": BOOKING_TIME.isoformat(),
    })
    assert booking.status_code == 201
    reservation_id = booking.json()["id"]
    identity["current"] = users["trainer"]
    listed = client.get("/api/v1/staff/me/reservations?from=2030-10-10&to=2030-10-10")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["member"]["id"] == str(identifiers["member_id"])
    assert client.get(f"/api/v1/staff/me/reservations/{reservation_id}").status_code == 200
    assert client.post(f"/api/v1/staff/me/reservations/{reservation_id}/complete").status_code == 409
    cancelled = client.post(f"/api/v1/staff/me/reservations/{reservation_id}/cancel", json={"reason": "店舗都合"})
    assert cancelled.status_code == 200
    with Session(engine) as session:
        entries = session.scalars(select(UsageEntry).where(UsageEntry.reservation_id == UUID(reservation_id))).all()
        assert {entry.entry_type for entry in entries} == {UsageEntryType.HOLD, UsageEntryType.RELEASE}
    identity["current"] = users["other_admin"]
    assert client.get(f"/api/v1/staff/me/reservations/{reservation_id}").status_code == 404


def test_staff_completion_consumes_reserved_usage(contract_environment) -> None:
    client, engine, identifiers, identity, users = contract_environment
    applied = apply_for_plan(client, identifiers["plan_id"])
    identity["current"] = users["admin"]
    assert client.post(f"/api/v1/management/contracts/{applied.json()['id']}/approve", json={}).status_code == 200
    identity["current"] = users["member"]
    booking = client.post("/api/v1/reservations", json={
        "store_id": str(identifiers["store_id"]),
        "menu_id": str(identifiers["menu_id"]),
        "starts_at": BOOKING_TIME.isoformat(),
    })
    assert booking.status_code == 201
    reservation_id = UUID(booking.json()["id"])
    with Session(engine) as session:
        reservation = session.get(Reservation, reservation_id)
        reservation.starts_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        reservation.ends_at = datetime(2020, 1, 1, 1, tzinfo=timezone.utc)
        session.commit()
    identity["current"] = users["trainer"]
    completed = client.post(f"/api/v1/staff/me/reservations/{reservation_id}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    with Session(engine) as session:
        entries = session.scalars(select(UsageEntry).where(UsageEntry.reservation_id == reservation_id)).all()
        assert {entry.entry_type for entry in entries} == {UsageEntryType.HOLD, UsageEntryType.CONSUME}


def test_application_rejects_inactive_plan_or_member(contract_environment) -> None:
    client, engine, identifiers, _, _ = contract_environment
    with Session(engine) as session:
        session.get(Plan, identifiers["plan_id"]).status = PlanStatus.INACTIVE
        session.commit()
    assert apply_for_plan(client, identifiers["plan_id"]).status_code == 409
    with Session(engine) as session:
        session.get(Plan, identifiers["plan_id"]).status = PlanStatus.ACTIVE
        session.get(Member, identifiers["member_id"]).status = MemberStatus.SUSPENDED
        session.commit()
    assert apply_for_plan(client, identifiers["plan_id"]).status_code == 403
