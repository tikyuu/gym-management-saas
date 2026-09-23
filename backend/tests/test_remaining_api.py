from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models.catalog
import app.models.contract
import app.models.member
import app.models.organization
import app.models.reservation
import app.models.scheduling
import app.models.staff
import app.models.store
import app.models.user_account
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.main import app
from app.models.base import Base
from app.models.member import Member, MemberConsent, MemberAuditHistory, MemberStatus
from app.models.catalog import Plan, PlanPeriodType, PlanUsageType
from app.models.contract import Contract, ContractStatus
from app.models.organization import AdminVerification, Organization, OrganizationStatus, SystemAdmin, SystemAdminAudit
from app.models.staff import Staff, StaffRole, StaffRoleType, StaffStatus, StaffStoreMembership
from app.models.user_account import UserAccount, UserAccountStatus
from app.services.cognito_admin import get_cognito_admin


@compiles(JSONB, "sqlite")
def compile_jsonb(element, compiler, **kwargs):
    return "JSON"


class FakeCognito:
    def __init__(self):
        self.enabled = []
        self.invited = []

    def verified_email(self, pool_id, subject):
        return "member@example.com"

    def invite(self, pool_id, email):
        self.invited.append((pool_id, email))
        return str(uuid4())

    def set_enabled(self, pool_id, subject, enabled):
        self.enabled.append((pool_id, subject, enabled))

    def delete(self, pool_id, subject):
        pass

    def subjects_for_email(self, pool_id, email):
        return []


@pytest.fixture
def api_environment(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "ap-northeast-1")
    monkeypatch.setenv("CUSTOMER_USER_POOL_ID", "customer")
    monkeypatch.setenv("STAFF_USER_POOL_ID", "staff")
    monkeypatch.setenv("SYSTEM_ADMIN_USER_POOL_ID", "system")
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, ExcludeConstraint):
                constraint.ddl_if(dialect="postgresql")
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    identities = {
        "member": AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="customer", authenticated_at=datetime.now(timezone.utc)),
        "admin": AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff"),
        "system": AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="system"),
    }
    with Session(engine) as session:
        organization = Organization(name="Gym", status=OrganizationStatus.ACTIVE)
        other_organization = Organization(name="Other Gym", status=OrganizationStatus.ACTIVE)
        accounts = {name: UserAccount(user_pool_id=user.user_pool_id, cognito_sub=user.cognito_sub)
                    for name, user in identities.items() if name != "member"}
        session.add_all([organization, other_organization, *accounts.values()])
        session.flush()
        staff = Staff(organization_id=organization.id, account_id=accounts["admin"].id,
                      name="Manager", status=StaffStatus.ACTIVE)
        system_admin = SystemAdmin(account_id=accounts["system"].id, name="Operator")
        session.add_all([staff, system_admin])
        session.flush()
        session.add(StaffRole(staff_id=staff.id, role=StaffRoleType.ORGANIZATION_ADMIN))
        session.commit()
        identifiers = {"organization": organization.id, "other_organization": other_organization.id,
                       "staff": staff.id, "system_account": accounts["system"].id}

    identity = {"current": identities["member"]}
    cognito = FakeCognito()

    def test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_current_user] = lambda: identity["current"]
    app.dependency_overrides[get_db_session] = test_session
    app.dependency_overrides[get_cognito_admin] = lambda: cognito
    try:
        with TestClient(app) as client:
            yield client, engine, identifiers, identity, identities, cognito
    finally:
        app.dependency_overrides.clear()


def test_member_registration_and_scoped_management(api_environment):
    client, engine, ids, identity, identities, _ = api_environment
    payload = {
        "organization_id": str(ids["organization"]), "name": "山田 太郎",
        "name_kana": "ヤマダ タロウ", "phone_number": "09012345678",
        "document_version": "v1",
    }
    response = client.post("/api/v1/members/me/registration", json=payload)
    assert response.status_code == 201, response.text
    member_id = response.json()["id"]
    assert client.post("/api/v1/members/me/registration", json=payload).status_code == 409
    with Session(engine) as session:
        assert session.scalar(select(MemberConsent).where(MemberConsent.member_id == UUID(member_id))) is not None
    identity["current"] = identities["admin"]
    assert client.get(f"/api/v1/management/members/{member_id}").status_code == 200
    correction = client.patch(f"/api/v1/management/members/{member_id}", json={
        "name": "山田 次郎", "reason": "本人申告の訂正",
    })
    assert correction.status_code == 200, correction.text
    with Session(engine) as session:
        assert session.scalar(select(MemberAuditHistory).where(MemberAuditHistory.member_id == UUID(member_id))) is not None
        other = Member(organization_id=ids["other_organization"], member_number="M-other",
                       name="Other", name_kana="OTHER", phone_number="09012345678")
        session.add(other)
        session.commit()
        other_id = other.id
    assert client.get(f"/api/v1/management/members/{other_id}").status_code == 404


def test_system_admin_requires_allowlisted_account(api_environment):
    client, engine, ids, identity, identities, _ = api_environment
    identity["current"] = identities["admin"]
    assert client.get("/api/v1/system-admin/organizations").status_code == 403
    identity["current"] = identities["system"]
    response = client.get("/api/v1/system-admin/organizations")
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 2
    created = client.post("/api/v1/system-admin/organizations", json={"name": "New Gym"})
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "preparing"
    change = client.patch(f"/api/v1/system-admin/organizations/{created.json()['id']}/status", json={
        "status": "active", "reason": "ready",
    })
    assert change.status_code == 409


def test_organization_termination_checks_only_its_own_contracts(api_environment):
    client, engine, ids, identity, identities, _ = api_environment
    with Session(engine) as session:
        member = Member(
            organization_id=ids["other_organization"], member_number="M-other",
            name="Other", name_kana="OTHER", phone_number="09012345678",
        )
        plan = Plan(
            organization_id=ids["other_organization"], name="Other plan",
            usage_type=PlanUsageType.UNLIMITED, period_type=PlanPeriodType.FIXED,
            period_months=1, price_yen=0,
        )
        session.add_all([member, plan])
        session.flush()
        session.add(Contract(
            member_id=member.id, plan_id=plan.id, plan_snapshot={"name": "Other plan"},
            status=ContractStatus.ACTIVE, starts_on=date(2030, 1, 1), ends_on=date(2030, 1, 31),
        ))
        session.commit()
    identity["current"] = identities["system"]
    response = client.patch(f"/api/v1/system-admin/organizations/{ids['organization']}/status", json={
        "status": "terminated", "reason": "End of service",
    })
    assert response.status_code == 200, response.text
    response = client.patch(f"/api/v1/system-admin/organizations/{ids['other_organization']}/status", json={
        "status": "terminated", "reason": "End of service",
    })
    assert response.status_code == 409, response.text


def test_staff_invite_deactivate_and_reactivate(api_environment):
    client, engine, ids, identity, identities, cognito = api_environment
    identity["current"] = identities["admin"]
    with Session(engine) as session:
        from app.models.store import Store
        store = Store(organization_id=ids["organization"], name="Main",
                      address="Tokyo", phone_number="0312345678")
        session.add(store)
        session.commit()
        store_id = store.id
    invited = client.post("/api/v1/staff", json={
        "name": "Trainer", "email": "trainer@example.com",
        "roles": [{"role": "trainer", "store_id": str(store_id)}],
    })
    assert invited.status_code == 201, invited.text
    staff_id = invited.json()["id"]
    assert cognito.invited == [("staff", "trainer@example.com")]
    stopped = client.post(f"/api/v1/staff/{staff_id}/deactivate")
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["status"] == "inactive"
    resumed = client.post(f"/api/v1/staff/{staff_id}/reactivate", json={
        "reason": "Rehired", "roles": [{"role": "trainer", "store_id": str(store_id)}],
    })
    assert resumed.status_code == 200, resumed.text
    assert cognito.enabled[-2][2] is False
    assert cognito.enabled[-1][2] is True


def test_store_manager_can_retry_deactivation_and_rehire_own_trainer(api_environment):
    client, engine, ids, identity, identities, _ = api_environment
    with Session(engine) as session:
        from app.models.store import Store
        store = Store(organization_id=ids["organization"], name="Main",
                      address="Tokyo", phone_number="0312345678")
        manager_user = AuthenticatedUser(cognito_sub=str(uuid4()), user_pool_id="staff")
        manager_account = UserAccount(user_pool_id="staff", cognito_sub=manager_user.cognito_sub)
        session.add_all([store, manager_account])
        session.flush()
        manager = Staff(organization_id=ids["organization"], account_id=manager_account.id,
                        name="Store manager", status=StaffStatus.ACTIVE)
        session.add(manager)
        session.flush()
        membership = StaffStoreMembership(staff_id=manager.id, store_id=store.id)
        session.add(membership)
        session.flush()
        session.add(StaffRole(staff_id=manager.id, store_membership_id=membership.id,
                              role=StaffRoleType.STORE_ADMIN))
        session.commit()
        store_id = store.id
    identity["current"] = manager_user
    profile = client.get("/api/v1/staff/me")
    assert profile.status_code == 200, profile.text
    assert profile.json()["roles"] == [{
        "role": "store_admin", "store": {"id": str(store_id), "name": "Main"},
    }]
    invited = client.post("/api/v1/staff", json={
        "name": "Trainer", "email": "trainer@example.com",
        "roles": [{"role": "trainer", "store_id": str(store_id)}],
    })
    assert invited.status_code == 201, invited.text
    assert client.post("/api/v1/staff", json={
        "name": "Escalation", "email": "escalation@example.com",
        "roles": [{"role": "store_admin", "store_id": str(store_id)}],
    }).status_code == 403
    path = f"/api/v1/staff/{invited.json()['id']}"
    invited_staff = client.get("/api/v1/staff", params={"status": "invited"}).json()["items"]
    assert any(item["stores"][0]["roles"] == ["trainer"] for item in invited_staff)
    assert client.post(f"{path}/deactivate").status_code == 200
    assert any(item["id"] == invited.json()["id"] for item in client.get(
        "/api/v1/staff", params={"status": "inactive"},
    ).json()["items"])
    assert client.get(path).status_code == 200
    assert client.post(f"{path}/deactivate").status_code == 200
    assert client.post(f"{path}/reactivate", json={
        "reason": "Rehired", "roles": [{"role": "trainer", "store_id": str(store_id)}],
    }).status_code == 200


def test_member_withdraw_rejoin_and_recent_login_for_deletion(api_environment):
    client, engine, ids, identity, identities, cognito = api_environment
    registered = client.post("/api/v1/members/me/registration", json={
        "organization_id": str(ids["organization"]), "name": "山田 太郎",
        "name_kana": "ヤマダ タロウ", "phone_number": "09012345678",
        "document_version": "v1",
    })
    assert registered.status_code == 201
    assert client.post("/api/v1/members/me/withdraw", json={"confirm": False}).status_code == 422
    withdrawn = client.post("/api/v1/members/me/withdraw", json={"confirm": True})
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["status"] == "withdrawn"
    rejoined = client.post("/api/v1/members/me/rejoin", json={"confirm": True})
    assert rejoined.status_code == 200, rejoined.text
    assert rejoined.json()["status"] == "active"
    identity["current"] = AuthenticatedUser(cognito_sub=identities["member"].cognito_sub, user_pool_id="customer")
    assert client.post("/api/v1/members/me/account-deletion", json={"confirm": True}).status_code == 403
    identity["current"] = identities["member"]
    deleted = client.post("/api/v1/members/me/account-deletion", json={"confirm": True})
    assert deleted.status_code == 202, deleted.text
    assert deleted.json()["status"] == "deletion_pending"
    assert cognito.enabled[-1][2] is False
    assert client.get("/api/v1/members/me").status_code == 403


def test_recovery_needs_verified_unused_record(api_environment):
    client, engine, ids, identity, identities, cognito = api_environment
    identity["current"] = identities["system"]
    organization = client.post("/api/v1/system-admin/organizations", json={"name": "Pending Gym"})
    assert organization.status_code == 201
    organization_id = organization.json()["id"]
    invited = client.post(f"/api/v1/system-admin/organizations/{organization_id}/initial-admin", json={
        "name": "Owner", "email": "owner@example.com",
    })
    assert invited.status_code == 201, invited.text
    staff_id = invited.json()["id"]
    recovery_path = f"/api/v1/system-admin/organizations/{organization_id}/recover-admin"
    request = {"staff_id": staff_id, "verification_reference": "case-001", "reason": "verified by operator"}
    assert client.post(recovery_path, json=request).status_code == 403
    with Session(engine) as session:
        staff = session.get(Staff, UUID(staff_id))
        staff.status = StaffStatus.INACTIVE
        account = session.get(UserAccount, staff.account_id)
        account.status = UserAccountStatus.DISABLED
        session.add(AdminVerification(
            organization_id=UUID(organization_id), staff_id=staff.id,
            reference="case-001", verified_by_account_id=ids["system_account"],
        ))
        session.commit()
    recovered = client.post(recovery_path, json=request)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "active"
    assert cognito.enabled[-1][2] is True
    assert client.post(recovery_path, json=request).status_code == 403
    with Session(engine) as session:
        assert len(session.scalars(select(SystemAdminAudit)).all()) == 1
