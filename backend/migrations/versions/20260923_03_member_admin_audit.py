"""Add member consent and audit records and explicit system administrators."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260923_03"
down_revision = "20260923_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_consents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("member_id", sa.Uuid(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("document_version", sa.String(64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "member_audit_histories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("member_id", sa.Uuid(), sa.ForeignKey("members.id"), nullable=False),
        sa.Column("executed_by_account_id", sa.Uuid(), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("previous_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "system_admins",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("user_accounts.id"), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "admin_verifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("staff_id", sa.Uuid(), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("reference", sa.String(128), nullable=False, unique=True),
        sa.Column("verified_by_account_id", sa.Uuid(), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "system_admin_audits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("reference", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "staff_status_histories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("staff_id", sa.Uuid(), sa.ForeignKey("staff.id"), nullable=False),
        sa.Column("executed_by_account_id", sa.Uuid(), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("previous_status", postgresql.ENUM(name="staff_status", create_type=False), nullable=False),
        sa.Column("new_status", postgresql.ENUM(name="staff_status", create_type=False), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "contract_adjustment_histories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contract_id", sa.Uuid(), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("executed_by_account_id", sa.Uuid(), sa.ForeignKey("user_accounts.id"), nullable=False),
        sa.Column("previous_ends_on", sa.Date(), nullable=True),
        sa.Column("new_ends_on", sa.Date(), nullable=True),
        sa.Column("usage_delta", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("contract_adjustment_histories")
    op.drop_table("staff_status_histories")
    op.drop_table("system_admin_audits")
    op.drop_table("admin_verifications")
    op.drop_table("system_admins")
    op.drop_table("member_audit_histories")
    op.drop_table("member_consents")
