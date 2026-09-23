"""Prevent overlapping active contract periods for one member."""

from alembic import op


revision = "20260923_02"
down_revision = "20260923_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE contracts ADD CONSTRAINT ex_contracts_member_active_period "
        "EXCLUDE USING gist ("
        "member_id WITH =, daterange(starts_on, ends_on, '[]') WITH &&"
        ") WHERE (status IN ('pending', 'scheduled', 'active', 'paused'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE contracts DROP CONSTRAINT ex_contracts_member_active_period")
