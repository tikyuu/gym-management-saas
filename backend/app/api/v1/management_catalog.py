from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.authorization import get_staff_access, require_writable_organization
from app.api.v1.contracts import eligible_plan_scope
from app.api.v1.members import get_member_profile
from app.api.v1.pagination import Page, page
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.catalog import (
    AvailabilityStatus,
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
from app.models.organization import OrganizationStatus
from app.models.member import MemberStatus
from app.models.staff import Staff, StaffRole, StaffRoleStatus, StaffRoleType, StaffStoreMembership, StaffStoreMembershipStatus
from app.models.store import Store, StoreStatus


router = APIRouter()


class MenuCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    duration_minutes: int = Field(ge=1, le=1440)


class MenuPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    status: MenuStatus | None = None


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str | None
    duration_minutes: int
    status: MenuStatus


class AvailabilityPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: AvailabilityStatus


class PlanFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    usage_type: PlanUsageType
    period_type: PlanPeriodType
    usage_limit: int | None = Field(default=None, ge=1)
    period_months: int = Field(ge=1)
    price_yen: int = Field(ge=0)
    carryover_limit: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_usage(self):
        if (self.usage_type == PlanUsageType.LIMITED) != (self.usage_limit is not None):
            raise ValueError("usage_limit must be set exactly for limited plans")
        carryover_required = self.usage_type == PlanUsageType.LIMITED and self.period_type == PlanPeriodType.RECURRING
        if carryover_required != (self.carryover_limit is not None):
            raise ValueError("carryover_limit is required only for limited recurring plans")
        return self


class PlanPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    usage_type: PlanUsageType | None = None
    period_type: PlanPeriodType | None = None
    usage_limit: int | None = Field(default=None, ge=1)
    period_months: int | None = Field(default=None, ge=1)
    price_yen: int | None = Field(default=None, ge=0)
    carryover_limit: int | None = Field(default=None, ge=0)
    status: PlanStatus | None = None


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    usage_type: PlanUsageType
    period_type: PlanPeriodType
    usage_limit: int | None
    period_months: int
    price_yen: int
    carryover_limit: int | None
    status: PlanStatus
    store_ids: list[UUID] | None = None
    menu_ids: list[UUID] | None = None


def unique_commit(db_session: Session) -> None:
    try:
        db_session.commit()
    except IntegrityError as error:
        db_session.rollback()
        raise HTTPException(status_code=409, detail="The resource conflicts with existing data.") from error


def scoped_menu(menu_id: UUID, organization_id: UUID, db_session: Session) -> Menu:
    menu = db_session.get(Menu, menu_id)
    if menu is None or menu.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Menu not found.")
    return menu


def scoped_plan(plan_id: UUID, organization_id: UUID, db_session: Session) -> Plan:
    plan = db_session.get(Plan, plan_id)
    if plan is None or plan.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return plan


def scoped_store(store_id: UUID, organization_id: UUID, db_session: Session) -> Store:
    store = db_session.get(Store, store_id)
    if store is None or store.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Store not found.")
    return store


@router.get("/management/menus", response_model=Page[MenuResponse])
def list_management_menus(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    store_id: UUID | None = None,
    status: MenuStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> Page[MenuResponse]:
    access = get_staff_access(current_user, db_session)
    if not access.organization_admin and not access.managed_store_ids:
        raise HTTPException(status_code=403, detail="Manager role required.")
    if store_id is not None:
        scoped_store(store_id, access.staff.organization_id, db_session)
        access.require_store_manager(store_id)
    query = select(Menu).where(Menu.organization_id == access.staff.organization_id)
    if store_id is not None:
        query = query.join(StoreMenu).where(StoreMenu.store_id == store_id)
    elif not access.organization_admin:
        query = query.join(StoreMenu).where(StoreMenu.store_id.in_(access.managed_store_ids)).distinct()
    if status is not None:
        query = query.where(Menu.status == status)
    if cursor is not None:
        query = query.where(Menu.id > cursor)
    menus = db_session.scalars(query.order_by(Menu.id).limit(limit + 1)).all()
    return page([MenuResponse.model_validate(menu) for menu in menus], limit)


@router.post("/management/menus", response_model=MenuResponse, status_code=201)
def create_menu(
    request: MenuCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MenuResponse:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    require_writable_organization(access)
    menu = Menu(organization_id=access.staff.organization_id, **request.model_dump())
    db_session.add(menu)
    unique_commit(db_session)
    db_session.refresh(menu)
    return MenuResponse.model_validate(menu)


@router.patch("/management/menus/{menu_id}", response_model=MenuResponse)
def update_menu(
    menu_id: UUID,
    request: MenuPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> MenuResponse:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    require_writable_organization(access)
    menu = scoped_menu(menu_id, access.staff.organization_id, db_session)
    changes = request.model_dump(exclude_unset=True)
    if not changes or any(value is None for field, value in changes.items() if field != "description"):
        raise HTTPException(status_code=422, detail="Valid changes are required.")
    for field, value in changes.items():
        setattr(menu, field, value)
    unique_commit(db_session)
    return MenuResponse.model_validate(menu)


@router.put("/management/stores/{store_id}/menus/{menu_id}")
def set_store_menu(
    store_id: UUID,
    menu_id: UUID,
    request: AvailabilityPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    scoped_store(store_id, access.staff.organization_id, db_session)
    access.require_store_manager(store_id)
    scoped_menu(menu_id, access.staff.organization_id, db_session)
    link = db_session.get(StoreMenu, (store_id, menu_id))
    if link is None:
        link = StoreMenu(store_id=store_id, menu_id=menu_id, status=request.status)
        db_session.add(link)
    else:
        link.status = request.status
    db_session.commit()
    return {"store_id": store_id, "menu_id": menu_id, "status": link.status}


@router.put("/management/staff/{staff_id}/store-memberships/{membership_id}/menus/{menu_id}")
def set_trainer_menu(
    staff_id: UUID,
    membership_id: UUID,
    menu_id: UUID,
    request: AvailabilityPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    require_writable_organization(access)
    trainer = db_session.get(Staff, staff_id)
    membership = db_session.get(StaffStoreMembership, membership_id)
    if trainer is None or trainer.organization_id != access.staff.organization_id or membership is None or membership.staff_id != staff_id or membership.status != StaffStoreMembershipStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Trainer membership not found.")
    access.require_store_manager(membership.store_id)
    scoped_menu(menu_id, access.staff.organization_id, db_session)
    store_menu = db_session.get(StoreMenu, (membership.store_id, menu_id))
    if store_menu is None or store_menu.status != AvailabilityStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Menu is not offered by the store.")
    trainer_role = db_session.scalar(select(StaffRole.id).where(
        StaffRole.staff_id == staff_id,
        StaffRole.store_membership_id == membership_id,
        StaffRole.role == StaffRoleType.TRAINER,
        StaffRole.status == StaffRoleStatus.ACTIVE,
    ))
    if trainer_role is None:
        raise HTTPException(status_code=409, detail="Active trainer role required.")
    link = db_session.get(TrainerMenu, (membership_id, menu_id))
    if link is None:
        link = TrainerMenu(staff_store_membership_id=membership_id, menu_id=menu_id, status=request.status)
        db_session.add(link)
    else:
        link.status = request.status
    db_session.commit()
    return {"staff_id": staff_id, "membership_id": membership_id, "menu_id": menu_id, "status": link.status}


@router.get("/plans", response_model=Page[PlanResponse])
def list_member_plans(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    store_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> Page[PlanResponse]:
    member, organization = get_member_profile(current_user, db_session)
    if member.status != MemberStatus.ACTIVE or organization.status != OrganizationStatus.ACTIVE:
        return Page(items=[], next_cursor=None)
    query = select(Plan).where(Plan.organization_id == member.organization_id, Plan.status == PlanStatus.ACTIVE)
    if store_id is not None:
        query = query.join(PlanStore).join(Store, Store.id == PlanStore.store_id).where(
            PlanStore.store_id == store_id,
            PlanStore.status == AvailabilityStatus.ACTIVE,
            Store.status == StoreStatus.ACTIVE,
        )
    if cursor is not None:
        query = query.where(Plan.id > cursor)
    plans = db_session.scalars(query.order_by(Plan.id)).all()
    visible_plans = []
    for plan in plans:
        store_ids, menu_ids = eligible_plan_scope(db_session, plan, member.organization_id)
        if not store_ids or not menu_ids:
            continue
        response = PlanResponse.model_validate(plan)
        response.store_ids = store_ids
        response.menu_ids = menu_ids
        visible_plans.append(response)
        if len(visible_plans) > limit:
            break
    return page(visible_plans, limit)


@router.get("/management/plans", response_model=Page[PlanResponse])
def list_management_plans(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
    status: PlanStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> Page[PlanResponse]:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    query = select(Plan).where(Plan.organization_id == access.staff.organization_id)
    if status is not None:
        query = query.where(Plan.status == status)
    if cursor is not None:
        query = query.where(Plan.id > cursor)
    plans = db_session.scalars(query.order_by(Plan.id).limit(limit + 1)).all()
    return page([PlanResponse.model_validate(plan) for plan in plans], limit)


@router.post("/management/plans", response_model=PlanResponse, status_code=201)
def create_plan(
    request: PlanFields,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlanResponse:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    require_writable_organization(access)
    plan = Plan(organization_id=access.staff.organization_id, **request.model_dump())
    db_session.add(plan)
    unique_commit(db_session)
    db_session.refresh(plan)
    return PlanResponse.model_validate(plan)


@router.patch("/management/plans/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: UUID,
    request: PlanPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> PlanResponse:
    access = get_staff_access(current_user, db_session)
    access.require_organization_admin()
    require_writable_organization(access)
    plan = scoped_plan(plan_id, access.staff.organization_id, db_session)
    changes = request.model_dump(exclude_unset=True)
    if not changes or any(value is None for field, value in changes.items() if field not in ("usage_limit", "carryover_limit")):
        raise HTTPException(status_code=422, detail="Valid changes are required.")
    candidate = {field: getattr(plan, field) for field in PlanFields.model_fields}
    candidate.update({field: value for field, value in changes.items() if field in candidate})
    try:
        PlanFields.model_validate(candidate)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="Invalid plan conditions.") from error
    for field, value in changes.items():
        setattr(plan, field, value)
    unique_commit(db_session)
    return PlanResponse.model_validate(plan)


def set_plan_link(
    plan_id: UUID,
    target_id: UUID,
    status: AvailabilityStatus,
    access,
    db_session: Session,
    target_model,
    link_model,
    link_field: str,
) -> dict:
    access.require_organization_admin()
    require_writable_organization(access)
    scoped_plan(plan_id, access.staff.organization_id, db_session)
    target = db_session.get(target_model, target_id)
    if target is None or target.organization_id != access.staff.organization_id:
        raise HTTPException(status_code=404, detail="Resource not found.")
    link = db_session.get(link_model, (plan_id, target_id))
    if link is None:
        link = link_model(plan_id=plan_id, **{link_field: target_id}, status=status)
        db_session.add(link)
    else:
        link.status = status
    db_session.commit()
    return {"plan_id": plan_id, link_field: target_id, "status": link.status}


@router.put("/management/plans/{plan_id}/stores/{store_id}")
def set_plan_store(
    plan_id: UUID,
    store_id: UUID,
    request: AvailabilityPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    return set_plan_link(plan_id, store_id, request.status, access, db_session, Store, PlanStore, "store_id")


@router.put("/management/plans/{plan_id}/menus/{menu_id}")
def set_plan_menu(
    plan_id: UUID,
    menu_id: UUID,
    request: AvailabilityPatch,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> dict:
    access = get_staff_access(current_user, db_session)
    return set_plan_link(plan_id, menu_id, request.status, access, db_session, Menu, PlanMenu, "menu_id")
