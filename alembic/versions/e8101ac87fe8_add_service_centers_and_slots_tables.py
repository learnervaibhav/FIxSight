"""Add service centers and slots tables

Revision ID: e8101ac87fe8
Revises: 89bf646f01f5
Create Date: 2026-05-23 01:13:10.814030

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e8101ac87fe8'
down_revision: Union[str, None] = '89bf646f01f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create service_centers table
    op.create_table(
        'service_centers',
        sa.Column('center_id', sa.String(36), nullable=False),
        sa.Column('center_name', sa.String(256), nullable=False),
        sa.Column('location', sa.String(256), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('operating_hours_start', sa.Integer(), nullable=False),
        sa.Column('operating_hours_end', sa.Integer(), nullable=False),
        sa.Column('max_capacity', sa.Integer(), nullable=False),
        sa.Column('current_occupancy', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('center_id')
    )
    op.create_index('ix_service_centers_center_id', 'service_centers', ['center_id'])
    op.create_index('ix_service_centers_location', 'service_centers', ['location'])
    
    # Create service_slots table
    op.create_table(
        'service_slots',
        sa.Column('slot_id', sa.String(36), nullable=False),
        sa.Column('center_id', sa.String(36), nullable=False),
        sa.Column('vehicle_id', sa.String(36), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(), nullable=False),
        sa.Column('duration_hours', sa.Float(), nullable=False),
        sa.Column('slot_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['center_id'], ['service_centers.center_id']),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id']),
        sa.PrimaryKeyConstraint('slot_id')
    )
    op.create_index('ix_service_slots_slot_id', 'service_slots', ['slot_id'])
    op.create_index('ix_service_slots_center_id', 'service_slots', ['center_id'])
    op.create_index('ix_service_slots_vehicle_id', 'service_slots', ['vehicle_id'])


def downgrade() -> None:
    # Drop service_slots table and indexes
    op.drop_index('ix_service_slots_vehicle_id', table_name='service_slots')
    op.drop_index('ix_service_slots_center_id', table_name='service_slots')
    op.drop_index('ix_service_slots_slot_id', table_name='service_slots')
    op.drop_table('service_slots')
    
    # Drop service_centers table and indexes
    op.drop_index('ix_service_centers_location', table_name='service_centers')
    op.drop_index('ix_service_centers_center_id', table_name='service_centers')
    op.drop_table('service_centers')

