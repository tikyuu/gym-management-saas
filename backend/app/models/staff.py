from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import value_enum


class StaffStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    INACTIVE = "inactive"


class StaffRoleType(StrEnum):
    ORGANIZATION_ADMIN = "organization_admin"
    STORE_ADMIN = "store_admin"
    TRAINER = "trainer"


class StaffRoleStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class StaffStoreMembershipStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id"),
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("user_accounts.id"),
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[StaffStatus] = mapped_column(
        value_enum(StaffStatus, name="staff_status"),
        default=StaffStatus.INVITED,
        server_default=StaffStatus.INVITED.value,
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


class StaffStoreMembership(Base):
    __tablename__ = "staff_store_memberships"
    __table_args__ = (
        CheckConstraint(
            "(status = 'active' AND ended_at IS NULL) "
            "OR (status = 'inactive' AND ended_at IS NOT NULL)",
            name="ck_staff_store_memberships_ended_at",
        ),
        Index(
            "uq_staff_store_memberships_active_staff_store",
            "staff_id",
            "store_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        UniqueConstraint(
            "id",
            "staff_id",
            name="uq_staff_store_memberships_id_staff_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    staff_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("staff.id"))
    store_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("stores.id"))
    status: Mapped[StaffStoreMembershipStatus] = mapped_column(
        value_enum(StaffStoreMembershipStatus, name="staff_store_membership_status"),
        default=StaffStoreMembershipStatus.ACTIVE,
        server_default=StaffStoreMembershipStatus.ACTIVE.value,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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


class StaffRole(Base):
    __tablename__ = "staff_roles"
    __table_args__ = (
        CheckConstraint(
            "(role = 'organization_admin' AND store_membership_id IS NULL) "
            "OR (role IN ('store_admin', 'trainer') AND store_membership_id IS NOT NULL)",
            name="ck_staff_roles_scope",
        ),
        CheckConstraint(
            "(status = 'active' AND revoked_at IS NULL) "
            "OR (status = 'inactive' AND revoked_at IS NOT NULL)",
            name="ck_staff_roles_revoked_at",
        ),
        Index(
            "uq_staff_roles_active_organization_admin",
            "staff_id",
            "role",
            unique=True,
            postgresql_where=text(
                "status = 'active' AND role = 'organization_admin'"
            ),
        ),
        Index(
            "uq_staff_roles_active_store_role",
            "staff_id",
            "store_membership_id",
            "role",
            unique=True,
            postgresql_where=text(
                "status = 'active' AND role IN ('store_admin', 'trainer')"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    staff_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("staff.id"))
    store_membership_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("staff_store_memberships.id"),
        nullable=True,
    )
    role: Mapped[StaffRoleType] = mapped_column(
        value_enum(StaffRoleType, name="staff_role_type"),
    )
    status: Mapped[StaffRoleStatus] = mapped_column(
        value_enum(StaffRoleStatus, name="staff_role_status"),
        default=StaffRoleStatus.ACTIVE,
        server_default=StaffRoleStatus.ACTIVE.value,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
