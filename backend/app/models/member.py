from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MemberStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint(
            "(status = 'withdrawn' AND withdrawn_at IS NOT NULL) "
            "OR (status IN ('active', 'suspended') AND withdrawn_at IS NULL)",
            name="ck_members_withdrawn_at",
        ),
        UniqueConstraint(
            "organization_id",
            "member_number",
            name="uq_members_organization_id_member_number",
        ),
        UniqueConstraint("account_id", name="uq_members_account_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id"),
    )
    account_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("user_accounts.id"),
        nullable=True,
    )
    member_number: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    name_kana: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str] = mapped_column(String(32))
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[MemberStatus] = mapped_column(
        Enum(MemberStatus, name="member_status"),
        default=MemberStatus.ACTIVE,
        server_default=MemberStatus.ACTIVE.value,
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
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
