"""add_project_members_and_test_datasets

Revision ID: 41b2c589a102
Revises: 26e1d42bde30
Create Date: 2026-11-10 17:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '41b2c589a102'
down_revision: Union[str, Sequence[str], None] = '26e1d42bde30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Check if project_members exists
    has_members = conn.execute(sa.text("SELECT to_regclass('public.project_members') IS NOT NULL")).scalar()
    if not has_members:
        op.create_table(
            'project_members',
            sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('role', sa.String(length=32), nullable=False, server_default='viewer'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('project_id', 'user_id', name='uq_project_user_member')
        )
        op.create_index(op.f('ix_project_members_project_id'), 'project_members', ['project_id'], unique=False)
        op.create_index(op.f('ix_project_members_user_id'), 'project_members', ['user_id'], unique=False)

    # Check if test_datasets exists
    has_datasets = conn.execute(sa.text("SELECT to_regclass('public.test_datasets') IS NOT NULL")).scalar()
    if not has_datasets:
        op.create_table(
            'test_datasets',
            sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
            sa.Column('project_id', sa.UUID(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(length=160), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('format', sa.String(length=32), nullable=False, server_default='json'),
            sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column('rows', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column('created_by', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_test_datasets_project_id'), 'test_datasets', ['project_id'], unique=False)
        op.create_index(op.f('ix_test_datasets_name'), 'test_datasets', ['name'], unique=False)


def downgrade() -> None:
    op.drop_table('test_datasets')
    op.drop_table('project_members')

