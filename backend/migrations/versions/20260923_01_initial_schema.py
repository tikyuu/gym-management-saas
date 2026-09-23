"""Create the initial application schema."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260923_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table('organizations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('status', postgresql.ENUM('preparing', 'active', 'suspended', 'terminated', name='organization_status'), server_default='preparing', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user_accounts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_pool_id', sa.String(length=128), nullable=True),
    sa.Column('cognito_sub', sa.String(length=36), nullable=True),
    sa.Column('status', postgresql.ENUM('active', 'disabled', 'deletion_pending', 'anonymized', name='user_account_status'), server_default='active', nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deletion_requested_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('anonymized_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(status = 'anonymized' AND user_pool_id IS NULL AND cognito_sub IS NULL) OR (status <> 'anonymized' AND user_pool_id IS NOT NULL AND cognito_sub IS NOT NULL)", name='ck_user_accounts_cognito_identity'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_pool_id', 'cognito_sub', name='uq_user_accounts_user_pool_id_cognito_sub')
    )
    op.create_table('members',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('account_id', sa.Uuid(), nullable=True),
    sa.Column('member_number', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('name_kana', sa.String(length=255), nullable=False),
    sa.Column('phone_number', sa.String(length=32), nullable=False),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('status', postgresql.ENUM('active', 'suspended', 'withdrawn', name='member_status'), server_default='active', nullable=False),
    sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(status = 'withdrawn' AND withdrawn_at IS NOT NULL) OR (status IN ('active', 'suspended') AND withdrawn_at IS NULL)", name='ck_members_withdrawn_at'),
    sa.ForeignKeyConstraint(['account_id'], ['user_accounts.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('account_id', name='uq_members_account_id'),
    sa.UniqueConstraint('organization_id', 'member_number', name='uq_members_organization_id_member_number')
    )
    op.create_table('menus',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('duration_minutes', sa.SmallInteger(), nullable=False),
    sa.Column('status', postgresql.ENUM('draft', 'active', 'inactive', name='menu_status'), server_default='draft', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('duration_minutes >= 1', name='ck_menus_duration_minutes'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'name', name='uq_menus_organization_id_name')
    )
    op.create_table('organization_status_histories',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('executed_by_account_id', sa.Uuid(), nullable=True),
    sa.Column('previous_status', postgresql.ENUM('preparing', 'active', 'suspended', 'terminated', name='organization_status'), nullable=False),
    sa.Column('new_status', postgresql.ENUM('preparing', 'active', 'suspended', 'terminated', name='organization_status'), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['executed_by_account_id'], ['user_accounts.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('plans',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('usage_type', postgresql.ENUM('limited', 'unlimited', name='plan_usage_type'), nullable=False),
    sa.Column('period_type', postgresql.ENUM('recurring', 'fixed', name='plan_period_type'), nullable=False),
    sa.Column('usage_limit', sa.Integer(), nullable=True),
    sa.Column('period_months', sa.SmallInteger(), nullable=False),
    sa.Column('price_yen', sa.Integer(), nullable=False),
    sa.Column('carryover_limit', sa.Integer(), nullable=True),
    sa.Column('status', postgresql.ENUM('draft', 'active', 'inactive', name='plan_status'), server_default='draft', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(usage_type = 'limited' AND period_type = 'recurring' AND carryover_limit IS NOT NULL AND carryover_limit >= 0) OR (NOT (usage_type = 'limited' AND period_type = 'recurring') AND carryover_limit IS NULL)", name='ck_plans_carryover_limit'),
    sa.CheckConstraint("(usage_type = 'limited' AND usage_limit IS NOT NULL AND usage_limit >= 1) OR (usage_type = 'unlimited' AND usage_limit IS NULL)", name='ck_plans_usage_limit'),
    sa.CheckConstraint('period_months >= 1', name='ck_plans_period_months'),
    sa.CheckConstraint('price_yen >= 0', name='ck_plans_price_yen'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'name', name='uq_plans_organization_id_name')
    )
    op.create_table('staff',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('account_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('status', postgresql.ENUM('invited', 'active', 'inactive', name='staff_status'), server_default='invited', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['user_accounts.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('account_id')
    )
    op.create_table('stores',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('address', sa.Text(), nullable=False),
    sa.Column('phone_number', sa.String(length=32), nullable=False),
    sa.Column('status', postgresql.ENUM('draft', 'active', 'suspended', 'closed', name='store_status'), server_default='draft', nullable=False),
    sa.Column('booking_interval_minutes', sa.SmallInteger(), server_default='30', nullable=False),
    sa.Column('free_cancellation_hours', sa.SmallInteger(), server_default='24', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('booking_interval_minutes IN (10, 15, 30)', name='ck_stores_booking_interval_minutes'),
    sa.CheckConstraint('free_cancellation_hours BETWEEN 0 AND 168', name='ck_stores_free_cancellation_hours'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('contracts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.Column('plan_id', sa.Uuid(), nullable=False),
    sa.Column('plan_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('status', postgresql.ENUM('pending', 'scheduled', 'active', 'paused', 'terminated', 'expired', 'rejected', name='contract_status'), server_default='pending', nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('starts_on <= ends_on', name='ck_contracts_date_range'),
    sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
    sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('plan_menus',
    sa.Column('plan_id', sa.Uuid(), nullable=False),
    sa.Column('menu_id', sa.Uuid(), nullable=False),
    sa.Column('status', postgresql.ENUM('active', 'inactive', name='availability_status'), server_default='active', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['menu_id'], ['menus.id'], ),
    sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
    sa.PrimaryKeyConstraint('plan_id', 'menu_id')
    )
    op.create_table('plan_stores',
    sa.Column('plan_id', sa.Uuid(), nullable=False),
    sa.Column('store_id', sa.Uuid(), nullable=False),
    sa.Column('status', postgresql.ENUM('active', 'inactive', name='availability_status'), server_default='active', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.PrimaryKeyConstraint('plan_id', 'store_id')
    )
    op.create_table('staff_store_memberships',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('staff_id', sa.Uuid(), nullable=False),
    sa.Column('store_id', sa.Uuid(), nullable=False),
    sa.Column('status', postgresql.ENUM('active', 'inactive', name='staff_store_membership_status'), server_default='active', nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(status = 'active' AND ended_at IS NULL) OR (status = 'inactive' AND ended_at IS NOT NULL)", name='ck_staff_store_memberships_ended_at'),
    sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('id', 'staff_id', name='uq_staff_store_memberships_id_staff_id')
    )
    op.create_index('uq_staff_store_memberships_active_staff_store', 'staff_store_memberships', ['staff_id', 'store_id'], unique=True, postgresql_where=sa.text("status = 'active'"))
    op.create_table('store_menus',
    sa.Column('store_id', sa.Uuid(), nullable=False),
    sa.Column('menu_id', sa.Uuid(), nullable=False),
    sa.Column('status', postgresql.ENUM('active', 'inactive', name='availability_status'), server_default='active', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['menu_id'], ['menus.id'], ),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.PrimaryKeyConstraint('store_id', 'menu_id')
    )
    op.create_table('store_regular_hours',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('store_id', sa.Uuid(), nullable=False),
    sa.Column('day_of_week', sa.SmallInteger(), nullable=False),
    sa.Column('opens_at', sa.Time(), nullable=False),
    sa.Column('closes_at', sa.Time(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('day_of_week BETWEEN 1 AND 7', name='ck_store_regular_hours_day_of_week'),
    sa.CheckConstraint('opens_at < closes_at', name='ck_store_regular_hours_time_range'),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('store_special_days',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('store_id', sa.Uuid(), nullable=False),
    sa.Column('business_date', sa.Date(), nullable=False),
    sa.Column('is_closed', sa.Boolean(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('store_id', 'business_date', name='uq_store_special_days_store_id_business_date')
    )
    op.create_table('contract_status_histories',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('executed_by_account_id', sa.Uuid(), nullable=True),
    sa.Column('previous_status', postgresql.ENUM('pending', 'scheduled', 'active', 'paused', 'terminated', 'expired', 'rejected', name='contract_status'), nullable=False),
    sa.Column('new_status', postgresql.ENUM('pending', 'scheduled', 'active', 'paused', 'terminated', 'expired', 'rejected', name='contract_status'), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ),
    sa.ForeignKeyConstraint(['executed_by_account_id'], ['user_accounts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('reservations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('member_id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('store_id', sa.Uuid(), nullable=False),
    sa.Column('staff_id', sa.Uuid(), nullable=False),
    sa.Column('staff_store_membership_id', sa.Uuid(), nullable=False),
    sa.Column('menu_id', sa.Uuid(), nullable=False),
    sa.Column('reservation_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', postgresql.ENUM('confirmed', 'completed', 'cancelled', 'no_show', name='reservation_status'), server_default='confirmed', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    postgresql.ExcludeConstraint((sa.column('member_id'), '='), (sa.text("tstzrange(starts_at, ends_at, '[)')"), '&&'), where=sa.text("status = 'confirmed'"), using='gist', name='ex_reservations_member_confirmed_time'),
    postgresql.ExcludeConstraint((sa.column('staff_id'), '='), (sa.text("tstzrange(starts_at, ends_at, '[)')"), '&&'), where=sa.text("status = 'confirmed'"), using='gist', name='ex_reservations_staff_confirmed_time'),
    sa.CheckConstraint('starts_at < ends_at', name='ck_reservations_time_range'),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ),
    sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
    sa.ForeignKeyConstraint(['menu_id'], ['menus.id'], ),
    sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
    sa.ForeignKeyConstraint(['staff_store_membership_id', 'staff_id'], ['staff_store_memberships.id', 'staff_store_memberships.staff_id'], name='fk_reservations_membership_staff'),
    sa.ForeignKeyConstraint(['staff_store_membership_id'], ['staff_store_memberships.id'], ),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('staff_roles',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('staff_id', sa.Uuid(), nullable=False),
    sa.Column('store_membership_id', sa.Uuid(), nullable=True),
    sa.Column('role', postgresql.ENUM('organization_admin', 'store_admin', 'trainer', name='staff_role_type'), nullable=False),
    sa.Column('status', postgresql.ENUM('active', 'inactive', name='staff_role_status'), server_default='active', nullable=False),
    sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(role = 'organization_admin' AND store_membership_id IS NULL) OR (role IN ('store_admin', 'trainer') AND store_membership_id IS NOT NULL)", name='ck_staff_roles_scope'),
    sa.CheckConstraint("(status = 'active' AND revoked_at IS NULL) OR (status = 'inactive' AND revoked_at IS NOT NULL)", name='ck_staff_roles_revoked_at'),
    sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
    sa.ForeignKeyConstraint(['store_membership_id'], ['staff_store_memberships.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('uq_staff_roles_active_organization_admin', 'staff_roles', ['staff_id', 'role'], unique=True, postgresql_where=sa.text("status = 'active' AND role = 'organization_admin'"))
    op.create_index('uq_staff_roles_active_store_role', 'staff_roles', ['staff_id', 'store_membership_id', 'role'], unique=True, postgresql_where=sa.text("status = 'active' AND role IN ('store_admin', 'trainer')"))
    op.create_table('store_special_day_hours',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('special_day_id', sa.Uuid(), nullable=False),
    sa.Column('opens_at', sa.Time(), nullable=False),
    sa.Column('closes_at', sa.Time(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('opens_at < closes_at', name='ck_store_special_day_hours_time_range'),
    sa.ForeignKeyConstraint(['special_day_id'], ['store_special_days.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('trainer_menus',
    sa.Column('staff_store_membership_id', sa.Uuid(), nullable=False),
    sa.Column('menu_id', sa.Uuid(), nullable=False),
    sa.Column('status', postgresql.ENUM('active', 'inactive', name='availability_status'), server_default='active', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['menu_id'], ['menus.id'], ),
    sa.ForeignKeyConstraint(['staff_store_membership_id'], ['staff_store_memberships.id'], ),
    sa.PrimaryKeyConstraint('staff_store_membership_id', 'menu_id')
    )
    op.create_table('work_shifts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('staff_id', sa.Uuid(), nullable=False),
    sa.Column('staff_store_membership_id', sa.Uuid(), nullable=False),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', postgresql.ENUM('scheduled', 'cancelled', name='work_shift_status'), server_default='scheduled', nullable=False),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    postgresql.ExcludeConstraint((sa.column('staff_id'), '='), (sa.text("tstzrange(starts_at, ends_at, '[)')"), '&&'), where=sa.text("status = 'scheduled'"), using='gist', name='ex_work_shifts_staff_scheduled_time'),
    sa.CheckConstraint("(status = 'scheduled' AND cancelled_at IS NULL) OR (status = 'cancelled' AND cancelled_at IS NOT NULL)", name='ck_work_shifts_cancelled_at'),
    sa.CheckConstraint('starts_at < ends_at', name='ck_work_shifts_time_range'),
    sa.ForeignKeyConstraint(['staff_id'], ['staff.id'], ),
    sa.ForeignKeyConstraint(['staff_store_membership_id', 'staff_id'], ['staff_store_memberships.id', 'staff_store_memberships.staff_id'], name='fk_work_shifts_membership_staff'),
    sa.ForeignKeyConstraint(['staff_store_membership_id'], ['staff_store_memberships.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('reservation_status_histories',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('reservation_id', sa.Uuid(), nullable=False),
    sa.Column('executed_by_account_id', sa.Uuid(), nullable=True),
    sa.Column('previous_status', postgresql.ENUM('confirmed', 'completed', 'cancelled', 'no_show', name='reservation_status'), nullable=False),
    sa.Column('new_status', postgresql.ENUM('confirmed', 'completed', 'cancelled', 'no_show', name='reservation_status'), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['executed_by_account_id'], ['user_accounts.id'], ),
    sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('unavailable_periods',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('work_shift_id', sa.Uuid(), nullable=False),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reason', postgresql.ENUM('break', 'other', name='unavailable_period_reason'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    postgresql.ExcludeConstraint((sa.column('work_shift_id'), '='), (sa.text("tstzrange(starts_at, ends_at, '[)')"), '&&'), using='gist', name='ex_unavailable_periods_work_shift_time'),
    sa.CheckConstraint('starts_at < ends_at', name='ck_unavailable_periods_time_range'),
    sa.ForeignKeyConstraint(['work_shift_id'], ['work_shifts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('usage_entries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('contract_id', sa.Uuid(), nullable=False),
    sa.Column('reservation_id', sa.Uuid(), nullable=True),
    sa.Column('executed_by_account_id', sa.Uuid(), nullable=True),
    sa.Column('entry_type', postgresql.ENUM('grant', 'carryover', 'hold', 'release', 'consume', 'expire', 'adjustment', name='usage_entry_type'), nullable=False),
    sa.Column('available_usage_delta', sa.Integer(), nullable=False),
    sa.Column('reserved_usage_delta', sa.Integer(), nullable=False),
    sa.Column('consumed_usage_delta', sa.Integer(), nullable=False),
    sa.Column('usage_period_starts_on', sa.Date(), nullable=False),
    sa.Column('usage_period_ends_on', sa.Date(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("entry_type <> 'adjustment' OR (reason IS NOT NULL AND executed_by_account_id IS NOT NULL)", name='ck_usage_entries_adjustment_context'),
    sa.CheckConstraint('usage_period_starts_on <= usage_period_ends_on', name='ck_usage_entries_period_range'),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ),
    sa.ForeignKeyConstraint(['executed_by_account_id'], ['user_accounts.id'], ),
    sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('usage_entries')
    op.drop_table('unavailable_periods')
    op.drop_table('reservation_status_histories')
    op.drop_table('work_shifts')
    op.drop_table('trainer_menus')
    op.drop_table('store_special_day_hours')
    op.drop_table('staff_roles')
    op.drop_table('reservations')
    op.drop_table('contract_status_histories')
    op.drop_table('store_special_days')
    op.drop_table('store_regular_hours')
    op.drop_table('store_menus')
    op.drop_table('staff_store_memberships')
    op.drop_table('plan_stores')
    op.drop_table('plan_menus')
    op.drop_table('contracts')
    op.drop_table('stores')
    op.drop_table('staff')
    op.drop_table('plans')
    op.drop_table('organization_status_histories')
    op.drop_table('menus')
    op.drop_table('members')
    op.drop_table('user_accounts')
    op.drop_table('organizations')
    op.execute('DROP TYPE work_shift_status')
    op.execute('DROP TYPE user_account_status')
    op.execute('DROP TYPE usage_entry_type')
    op.execute('DROP TYPE unavailable_period_reason')
    op.execute('DROP TYPE store_status')
    op.execute('DROP TYPE staff_store_membership_status')
    op.execute('DROP TYPE staff_status')
    op.execute('DROP TYPE staff_role_type')
    op.execute('DROP TYPE staff_role_status')
    op.execute('DROP TYPE reservation_status')
    op.execute('DROP TYPE plan_usage_type')
    op.execute('DROP TYPE plan_status')
    op.execute('DROP TYPE plan_period_type')
    op.execute('DROP TYPE organization_status')
    op.execute('DROP TYPE menu_status')
    op.execute('DROP TYPE member_status')
    op.execute('DROP TYPE contract_status')
    op.execute('DROP TYPE availability_status')
