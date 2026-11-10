"""create_initial_enterprise_tables

Revision ID: 26e1d42bde30
Revises: 
Create Date: 2026-11-10 11:08:13.687295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '26e1d42bde30'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgcrypto for gen_random_uuid() if not present
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # 2. Create roles table
    op.create_table('roles',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)

    # 3. Migrate users table non-destructively
    # Check if users table exists
    conn = op.get_bind()
    has_users = conn.execute(sa.text("SELECT to_regclass('public.users') IS NOT NULL")).scalar()

    if has_users:
        # Add new columns to existing users table
        op.add_column('users', sa.Column('uuid', sa.UUID(), nullable=True, server_default=sa.text('gen_random_uuid()')))
        op.execute('UPDATE users SET uuid = gen_random_uuid() WHERE uuid IS NULL;')
        op.alter_column('users', 'uuid', nullable=False)

        op.add_column('users', sa.Column('full_name', sa.String(length=160), nullable=True))
        op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False))
        op.add_column('users', sa.Column('is_superuser', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

        # Make Siddhartha superuser/owner if exists
        op.execute("UPDATE users SET full_name = 'Siddhartha', is_superuser = true WHERE email ILIKE '%siddhartha%';")

        # Swap id from BIGINT to UUID
        op.execute("ALTER TABLE users RENAME COLUMN id TO legacy_id;")
        op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_pkey;")
        op.execute("ALTER TABLE users RENAME COLUMN uuid TO id;")
        op.execute("ALTER TABLE users ADD PRIMARY KEY (id);")

        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    else:
        op.create_table('users',
            sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
            sa.Column('email', sa.String(length=320), nullable=False),
            sa.Column('password_hash', sa.String(length=256), nullable=False),
            sa.Column('full_name', sa.String(length=160), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
            sa.Column('is_superuser', sa.Boolean(), server_default=sa.text('false'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 4. User roles junction table
    op.create_table('user_roles',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )

    # 5. Projects table
    op.create_table('projects',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_name'), 'projects', ['name'], unique=False)

    # Migrate existing workspaces into projects if table exists
    has_workspaces = conn.execute(sa.text("SELECT to_regclass('public.workspaces') IS NOT NULL")).scalar()
    if has_workspaces:
        op.execute("""
            INSERT INTO projects (name, description, owner_id, created_at, updated_at)
            SELECT w.name, 'Migrated workspace', u.id, w.created_at, w.created_at
            FROM workspaces w
            LEFT JOIN users u ON TRUE
            LIMIT 1;
        """)

    # 6. Environments table
    op.create_table('environments',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('base_url', sa.String(length=512), nullable=False),
        sa.Column('allowed_domains', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('variables_encrypted', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_environments_name'), 'environments', ['name'], unique=False)
    op.create_index(op.f('ix_environments_project_id'), 'environments', ['project_id'], unique=False)

    # 7. Credentials table
    op.create_table('credentials',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('credential_type', sa.String(length=32), nullable=False),
        sa.Column('username', sa.String(length=256), nullable=True),
        sa.Column('secret_encrypted', sa.Text(), nullable=False),
        sa.Column('domain_scope', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_credentials_name'), 'credentials', ['name'], unique=False)
    op.create_index(op.f('ix_credentials_project_id'), 'credentials', ['project_id'], unique=False)

    # 8. Automation Definitions table
    op.create_table('automation_definitions',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), default='draft', nullable=False),
        sa.Column('current_version_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_definitions_name'), 'automation_definitions', ['name'], unique=False)
    op.create_index(op.f('ix_automation_definitions_project_id'), 'automation_definitions', ['project_id'], unique=False)
    op.create_index(op.f('ix_automation_definitions_type'), 'automation_definitions', ['type'], unique=False)

    # Migrate existing workflows into automation_definitions
    has_workflows = conn.execute(sa.text("SELECT to_regclass('public.workflows') IS NOT NULL")).scalar()
    if has_workflows:
        op.execute("""
            INSERT INTO automation_definitions (project_id, type, name, description, status, created_at, updated_at)
            SELECT p.id, 'flow', w.name, 'Migrated workflow', 'draft', w.created_at, w.created_at
            FROM workflows w
            CROSS JOIN (SELECT id FROM projects LIMIT 1) p;
        """)

    # 9. Definition Versions table
    op.create_table('definition_versions',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('definition_id', sa.UUID(), nullable=False),
        sa.Column('version_num', sa.Integer(), nullable=False),
        sa.Column('definition_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
        sa.Column('is_published', sa.Boolean(), default=False, nullable=False),
        sa.Column('published_by', sa.UUID(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['definition_id'], ['automation_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['published_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('definition_id', 'version_num', name='uq_definition_version_num')
    )
    op.create_index(op.f('ix_definition_versions_definition_id'), 'definition_versions', ['definition_id'], unique=False)

    # 10. Schedules table
    op.create_table('schedules',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('definition_id', sa.UUID(), nullable=False),
        sa.Column('environment_id', sa.UUID(), nullable=False),
        sa.Column('cron_expression', sa.String(length=64), nullable=False),
        sa.Column('timezone', sa.String(length=64), server_default='Asia/Kolkata', nullable=False),
        sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['definition_id'], ['automation_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['environment_id'], ['environments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_schedules_definition_id'), 'schedules', ['definition_id'], unique=False)
    op.create_index(op.f('ix_schedules_is_enabled'), 'schedules', ['is_enabled'], unique=False)

    # 11. Executions table
    op.create_table('executions',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('definition_id', sa.UUID(), nullable=False),
        sa.Column('definition_version_id', sa.UUID(), nullable=False),
        sa.Column('environment_id', sa.UUID(), nullable=True),
        sa.Column('trigger_type', sa.String(length=32), nullable=False),
        sa.Column('triggered_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='queued', nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['definition_id'], ['automation_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['definition_version_id'], ['definition_versions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['environment_id'], ['environments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_executions_definition_id'), 'executions', ['definition_id'], unique=False)
    op.create_index(op.f('ix_executions_project_id'), 'executions', ['project_id'], unique=False)
    op.create_index(op.f('ix_executions_session_id'), 'executions', ['session_id'], unique=False)
    op.create_index(op.f('ix_executions_status'), 'executions', ['status'], unique=False)
    op.create_index(op.f('ix_executions_trigger_type'), 'executions', ['trigger_type'], unique=False)

    # 12. Execution Steps table
    op.create_table('execution_steps',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.String(length=64), nullable=True),
        sa.Column('step_type', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('result_data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('screenshot_path', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_steps_execution_id'), 'execution_steps', ['execution_id'], unique=False)
    op.create_index(op.f('ix_execution_steps_status'), 'execution_steps', ['status'], unique=False)

    # 13. Execution Logs table
    op.create_table('execution_logs',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=True),
        sa.Column('level', sa.String(length=16), server_default='INFO', nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_redacted', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['step_id'], ['execution_steps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_logs_execution_id'), 'execution_logs', ['execution_id'], unique=False)

    # 14. Element Profiles table
    op.create_table('element_profiles',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('logical_id', sa.String(length=120), nullable=False),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.Column('element_type', sa.String(length=64), nullable=False),
        sa.Column('page_context', sa.String(length=120), nullable=False),
        sa.Column('original_text', sa.String(length=256), nullable=True),
        sa.Column('stable_attributes', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('structural_fingerprint', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'logical_id', name='uq_project_logical_id')
    )
    op.create_index(op.f('ix_element_profiles_logical_id'), 'element_profiles', ['logical_id'], unique=False)
    op.create_index(op.f('ix_element_profiles_page_context'), 'element_profiles', ['page_context'], unique=False)
    op.create_index(op.f('ix_element_profiles_project_id'), 'element_profiles', ['project_id'], unique=False)

    # 15. Locator History table
    op.create_table('locator_history',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('element_profile_id', sa.UUID(), nullable=False),
        sa.Column('locator_type', sa.String(length=32), nullable=False),
        sa.Column('locator_value', sa.String(length=512), nullable=False),
        sa.Column('success_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['element_profile_id'], ['element_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_locator_history_element_profile_id'), 'locator_history', ['element_profile_id'], unique=False)

    # 16. Healing Events table
    op.create_table('healing_events',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('element_profile_id', sa.UUID(), nullable=False),
        sa.Column('original_locator', sa.String(length=512), nullable=False),
        sa.Column('healed_locator', sa.String(length=512), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('scoring_breakdown', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('is_approved', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['element_profile_id'], ['element_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_healing_events_decision'), 'healing_events', ['decision'], unique=False)
    op.create_index(op.f('ix_healing_events_element_profile_id'), 'healing_events', ['element_profile_id'], unique=False)
    op.create_index(op.f('ix_healing_events_execution_id'), 'healing_events', ['execution_id'], unique=False)

    # 17. Approvals table
    op.create_table('approvals',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('healing_event_id', sa.UUID(), nullable=False),
        sa.Column('requested_by', sa.UUID(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['healing_event_id'], ['healing_events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approvals_healing_event_id'), 'approvals', ['healing_event_id'], unique=False)
    op.create_index(op.f('ix_approvals_status'), 'approvals', ['status'], unique=False)

    # 18. Artifacts table
    op.create_table('artifacts',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('artifact_type', sa.String(length=32), nullable=False),
        sa.Column('file_path', sa.String(length=512), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(length=64), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_artifacts_artifact_type'), 'artifacts', ['artifact_type'], unique=False)
    op.create_index(op.f('ix_artifacts_execution_id'), 'artifacts', ['execution_id'], unique=False)
    op.create_index(op.f('ix_artifacts_sha256_hash'), 'artifacts', ['sha256_hash'], unique=False)

    # 19. DOM Snapshots table
    op.create_table('dom_snapshots',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('page_url', sa.String(length=1024), nullable=False),
        sa.Column('snapshot_path', sa.String(length=512), nullable=False),
        sa.Column('element_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dom_snapshots_execution_id'), 'dom_snapshots', ['execution_id'], unique=False)

    # 20. Audit Logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('client_ip', sa.String(length=64), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    pass
