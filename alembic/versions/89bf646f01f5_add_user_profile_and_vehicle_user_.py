"""Add user profile and vehicle user association

Revision ID: 89bf646f01f5
Revises: f0ecdf081397
Create Date: 2026-05-10 14:39:40.685928

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89bf646f01f5'
down_revision: Union[str, None] = 'f0ecdf081397'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('email', sa.String(256), nullable=False, unique=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('location', sa.String(256), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('ix_users_user_id', 'users', ['user_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Add user_id and location columns to vehicles table
    op.add_column('vehicles', sa.Column('user_id', sa.String(36), nullable=True))
    op.add_column('vehicles', sa.Column('location', sa.String(256), nullable=True))
    
    # Create foreign key constraint from vehicles to users
    op.create_foreign_key(
        op.f('vehicles_user_id_fkey'),
        'vehicles',
        'users',
        ['user_id'],
        ['user_id']
    )
    
    # Create index on user_id
    op.create_index('ix_vehicles_user_id', 'vehicles', ['user_id'])


def downgrade() -> None:
    # Drop index and foreign key
    op.drop_index('ix_vehicles_user_id', table_name='vehicles')
    op.drop_constraint(op.f('vehicles_user_id_fkey'), 'vehicles', type_='foreignkey')
    
    # Drop columns from vehicles table
    op.drop_column('vehicles', 'location')
    op.drop_column('vehicles', 'user_id')
    
    # Drop users table and indexes
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_user_id', table_name='users')
    op.drop_table('users')
