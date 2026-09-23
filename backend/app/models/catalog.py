from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import value_enum


class MenuStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


class AvailabilityStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class PlanUsageType(StrEnum):
    LIMITED = "limited"
    UNLIMITED = "unlimited"


class PlanPeriodType(StrEnum):
    RECURRING = "recurring"
    FIXED = "fixed"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


class Menu(Base):
    __tablename__ = "menus"
    __table_args__ = (
        CheckConstraint(
            "duration_minutes >= 1",
            name="ck_menus_duration_minutes",
        ),
        UniqueConstraint(
            "organization_id",
            "name",
            name="uq_menus_organization_id_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id"),
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[MenuStatus] = mapped_column(
        value_enum(MenuStatus, name="menu_status"),
        default=MenuStatus.DRAFT,
        server_default=MenuStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class StoreMenu(Base):
    __tablename__ = "store_menus"

    store_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("stores.id"),
        primary_key=True,
    )
    menu_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("menus.id"),
        primary_key=True,
    )
    status: Mapped[AvailabilityStatus] = mapped_column(
        value_enum(AvailabilityStatus, name="availability_status"),
        default=AvailabilityStatus.ACTIVE,
        server_default=AvailabilityStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TrainerMenu(Base):
    __tablename__ = "trainer_menus"

    staff_store_membership_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("staff_store_memberships.id"),
        primary_key=True,
    )
    menu_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("menus.id"),
        primary_key=True,
    )
    status: Mapped[AvailabilityStatus] = mapped_column(
        value_enum(AvailabilityStatus, name="availability_status"),
        default=AvailabilityStatus.ACTIVE,
        server_default=AvailabilityStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint(
            "(usage_type = 'limited' AND usage_limit IS NOT NULL AND usage_limit >= 1) "
            "OR (usage_type = 'unlimited' AND usage_limit IS NULL)",
            name="ck_plans_usage_limit",
        ),
        CheckConstraint(
            "(usage_type = 'limited' AND period_type = 'recurring' "
            "AND carryover_limit IS NOT NULL AND carryover_limit >= 0) "
            "OR (NOT (usage_type = 'limited' AND period_type = 'recurring') "
            "AND carryover_limit IS NULL)",
            name="ck_plans_carryover_limit",
        ),
        CheckConstraint(
            "period_months >= 1",
            name="ck_plans_period_months",
        ),
        CheckConstraint(
            "price_yen >= 0",
            name="ck_plans_price_yen",
        ),
        UniqueConstraint(
            "organization_id",
            "name",
            name="uq_plans_organization_id_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id"),
    )
    name: Mapped[str] = mapped_column(String(255))
    usage_type: Mapped[PlanUsageType] = mapped_column(
        value_enum(PlanUsageType, name="plan_usage_type"),
    )
    period_type: Mapped[PlanPeriodType] = mapped_column(
        value_enum(PlanPeriodType, name="plan_period_type"),
    )
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    period_months: Mapped[int] = mapped_column(SmallInteger)
    price_yen: Mapped[int] = mapped_column(Integer)
    carryover_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[PlanStatus] = mapped_column(
        value_enum(PlanStatus, name="plan_status"),
        default=PlanStatus.DRAFT,
        server_default=PlanStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PlanStore(Base):
    __tablename__ = "plan_stores"

    plan_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("plans.id"),
        primary_key=True,
    )
    store_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("stores.id"),
        primary_key=True,
    )
    status: Mapped[AvailabilityStatus] = mapped_column(
        value_enum(AvailabilityStatus, name="availability_status"),
        default=AvailabilityStatus.ACTIVE,
        server_default=AvailabilityStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class PlanMenu(Base):
    __tablename__ = "plan_menus"

    plan_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("plans.id"),
        primary_key=True,
    )
    menu_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("menus.id"),
        primary_key=True,
    )
    status: Mapped[AvailabilityStatus] = mapped_column(
        value_enum(AvailabilityStatus, name="availability_status"),
        default=AvailabilityStatus.ACTIVE,
        server_default=AvailabilityStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
