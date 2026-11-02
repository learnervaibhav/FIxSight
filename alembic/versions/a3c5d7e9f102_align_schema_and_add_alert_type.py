"""Align schema with models; add alert type and slot reason

Revision ID: a3c5d7e9f102
Revises: e8101ac87fe8
Create Date: 2026-11-01 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c5d7e9f102'
down_revision: Union[str, None] = 'e8101ac87fe8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Vehicles always belong to a user and have a location (seeders set both).
    op.alter_column('vehicles', 'user_id', existing_type=sa.String(36), nullable=False)
    op.alter_column('vehicles', 'location', existing_type=sa.String(256), nullable=False)

    # Match ORM lengths for service slots.
    op.alter_column('service_slots', 'vehicle_id', existing_type=sa.String(36), type_=sa.String(16), existing_nullable=False)
    op.alter_column('service_slots', 'slot_status', existing_type=sa.String(50), type_=sa.String(16), existing_nullable=False)
    op.add_column('service_slots', sa.Column('reason', sa.String(128), nullable=True))
    op.create_index('ix_service_slots_slot_status', 'service_slots', ['slot_status'])

    # Distinguish fault alerts from booking / completion notifications.
    op.add_column('alert_logs', sa.Column('alert_type', sa.String(32), nullable=False, server_default='fault'))


def downgrade() -> None:
    op.drop_column('alert_logs', 'alert_type')

    op.drop_index('ix_service_slots_slot_status', table_name='service_slots')
    op.drop_column('service_slots', 'reason')
    op.alter_column('service_slots', 'slot_status', existing_type=sa.String(16), type_=sa.String(50), existing_nullable=False)
    op.alter_column('service_slots', 'vehicle_id', existing_type=sa.String(16), type_=sa.String(36), existing_nullable=False)

    op.alter_column('vehicles', 'location', existing_type=sa.String(256), nullable=True)
    op.alter_column('vehicles', 'user_id', existing_type=sa.String(36), nullable=True)
