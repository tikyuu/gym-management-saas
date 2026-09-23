from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.members import get_member_profile
from app.auth.cognito import AuthenticatedUser, get_current_user
from app.database import get_db_session
from app.models.catalog import AvailabilityStatus, Menu, MenuStatus, StoreMenu
from app.models.contract import Contract, ContractStatus
from app.models.member import Member, MemberStatus
from app.models.organization import OrganizationStatus
from app.models.store import Store, StoreStatus


router = APIRouter()


class PlanSnapshot(BaseModel):
    store_ids: list[UUID]
    menu_ids: list[UUID]


class StoreResponse(BaseModel):
    id: UUID
    name: str
    address: str


class MenuResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    duration_minutes: int


def booking_snapshots(member: Member, db_session: Session) -> list[PlanSnapshot]:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    snapshots = db_session.scalars(
        select(Contract.plan_snapshot).where(
            Contract.member_id == member.id,
            Contract.status.in_((ContractStatus.ACTIVE, ContractStatus.SCHEDULED)),
            Contract.ends_on >= today,
        )
    ).all()
    return [PlanSnapshot.model_validate(snapshot) for snapshot in snapshots]


@router.get("/stores", response_model=list[StoreResponse])
def list_booking_stores(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[StoreResponse]:
    member, organization = get_member_profile(current_user, db_session)
    if member.status != MemberStatus.ACTIVE or organization.status != OrganizationStatus.ACTIVE:
        return []

    store_ids = {
        store_id
        for snapshot in booking_snapshots(member, db_session)
        for store_id in snapshot.store_ids
    }
    if not store_ids:
        return []

    stores = db_session.scalars(
        select(Store)
        .where(
            Store.id.in_(store_ids),
            Store.organization_id == organization.id,
            Store.status == StoreStatus.ACTIVE,
        )
        .order_by(Store.name, Store.id)
    ).all()
    return [StoreResponse(id=store.id, name=store.name, address=store.address) for store in stores]


@router.get("/stores/{store_id}/menus", response_model=list[MenuResponse])
def list_booking_menus(
    store_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db_session: Annotated[Session, Depends(get_db_session)],
) -> list[MenuResponse]:
    member, organization = get_member_profile(current_user, db_session)
    snapshots = (
        booking_snapshots(member, db_session)
        if member.status == MemberStatus.ACTIVE
        and organization.status == OrganizationStatus.ACTIVE
        else []
    )
    eligible_snapshots = [
        snapshot for snapshot in snapshots if store_id in snapshot.store_ids
    ]
    store = db_session.scalar(
        select(Store).where(
            Store.id == store_id,
            Store.organization_id == organization.id,
            Store.status == StoreStatus.ACTIVE,
        )
    )
    if store is None or not eligible_snapshots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store is unavailable.",
        )

    menu_ids = {
        menu_id
        for snapshot in eligible_snapshots
        for menu_id in snapshot.menu_ids
    }
    if not menu_ids:
        return []

    menus = db_session.scalars(
        select(Menu)
        .join(StoreMenu, StoreMenu.menu_id == Menu.id)
        .where(
            StoreMenu.store_id == store_id,
            StoreMenu.status == AvailabilityStatus.ACTIVE,
            Menu.id.in_(menu_ids),
            Menu.organization_id == organization.id,
            Menu.status == MenuStatus.ACTIVE,
        )
        .order_by(Menu.name, Menu.id)
    ).all()
    return [
        MenuResponse(
            id=menu.id,
            name=menu.name,
            description=menu.description,
            duration_minutes=menu.duration_minutes,
        )
        for menu in menus
    ]
