"""initial_schema

Revision ID: f0ecdf081397
Revises: 
Create Date: 2026-03-18 23:26:43.777502

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0ecdf081397'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create vehicles table
    op.create_table(
        'vehicles',
        sa.Column('vehicle_id', sa.String(16), nullable=False),
        sa.Column('manufacture_year', sa.Integer(), nullable=False),
        sa.Column('initial_odometer', sa.Integer(), nullable=False),
        sa.Column('engine_type', sa.String(64), nullable=False),
        sa.Column('driving_profile', sa.String(32), nullable=False),
        sa.Column('region', sa.String(64), nullable=False),
        sa.Column('average_daily_distance', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('vehicle_id')
    )
    op.create_index('ix_vehicles_vehicle_id', 'vehicles', ['vehicle_id'])

    # Create telemetry_readings table
    op.create_table(
        'telemetry_readings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.String(16), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('engine_rpm', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('engine_load', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('coolant_temperature', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('oil_temperature', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('oil_pressure', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('fuel_rate', sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column('short_term_fuel_trim', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('long_term_fuel_trim', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('mass_air_flow', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('intake_manifold_pressure', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('battery_voltage', sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column('alternator_voltage', sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column('gear_position', sa.Integer(), nullable=False),
        sa.Column('transmission_temperature', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('o2_sensor_voltage', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('egr_position', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('vehicle_speed', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('throttle_position', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('cumulative_engine_hours', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('rolling_mean_temp', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('rolling_std_temp', sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column('rolling_slope_oil_pressure', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('harsh_acceleration_count', sa.Integer(), nullable=False),
        sa.Column('idle_time_ratio', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('degradation_index', sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column('health_score', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('rul_hours', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id'], )
    )
    op.create_index('ix_telemetry_readings_vehicle_id', 'telemetry_readings', ['vehicle_id'])
    op.create_index('ix_telemetry_readings_timestamp', 'telemetry_readings', ['timestamp'])
    op.create_index('ix_telemetry_readings_vehicle_id_timestamp', 'telemetry_readings', ['vehicle_id', 'timestamp'])

    # Create fault_predictions table
    op.create_table(
        'fault_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.String(16), nullable=False),
        sa.Column('telemetry_reading_id', sa.Integer(), nullable=True),
        sa.Column('fault_label', sa.String(128), nullable=False),
        sa.Column('fault_probability', sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column('severity', sa.String(16), nullable=True),
        sa.Column('llm_explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id'], ),
        sa.ForeignKeyConstraint(['telemetry_reading_id'], ['telemetry_readings.id'], )
    )
    op.create_index('ix_fault_predictions_vehicle_id', 'fault_predictions', ['vehicle_id'])
    op.create_index('ix_fault_predictions_telemetry_reading_id', 'fault_predictions', ['telemetry_reading_id'])
    op.create_index('ix_fault_predictions_vehicle_id_created_at', 'fault_predictions', ['vehicle_id', 'created_at'])

    # Create rul_predictions table
    op.create_table(
        'rul_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.String(16), nullable=False),
        sa.Column('telemetry_reading_id', sa.Integer(), nullable=True),
        sa.Column('rul_hours', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id'], ),
        sa.ForeignKeyConstraint(['telemetry_reading_id'], ['telemetry_readings.id'], )
    )
    op.create_index('ix_rul_predictions_vehicle_id', 'rul_predictions', ['vehicle_id'])
    op.create_index('ix_rul_predictions_telemetry_reading_id', 'rul_predictions', ['telemetry_reading_id'])
    op.create_index('ix_rul_predictions_vehicle_id_created_at', 'rul_predictions', ['vehicle_id', 'created_at'])

    # Create alert_logs table
    op.create_table(
        'alert_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.String(16), nullable=False),
        sa.Column('fault_prediction_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(16), nullable=False, server_default='sms'),
        sa.Column('recipient', sa.String(64), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default='queued'),
        sa.Column('alert_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.vehicle_id'], ),
        sa.ForeignKeyConstraint(['fault_prediction_id'], ['fault_predictions.id'], )
    )
    op.create_index('ix_alert_logs_vehicle_id', 'alert_logs', ['vehicle_id'])
    op.create_index('ix_alert_logs_fault_prediction_id', 'alert_logs', ['fault_prediction_id'])
    op.create_index('ix_alert_logs_vehicle_id_created_at', 'alert_logs', ['vehicle_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_alert_logs_vehicle_id_created_at', table_name='alert_logs')
    op.drop_index('ix_alert_logs_fault_prediction_id', table_name='alert_logs')
    op.drop_index('ix_alert_logs_vehicle_id', table_name='alert_logs')
    op.drop_table('alert_logs')
    
    op.drop_index('ix_rul_predictions_vehicle_id_created_at', table_name='rul_predictions')
    op.drop_index('ix_rul_predictions_telemetry_reading_id', table_name='rul_predictions')
    op.drop_index('ix_rul_predictions_vehicle_id', table_name='rul_predictions')
    op.drop_table('rul_predictions')
    
    op.drop_index('ix_fault_predictions_vehicle_id_created_at', table_name='fault_predictions')
    op.drop_index('ix_fault_predictions_telemetry_reading_id', table_name='fault_predictions')
    op.drop_index('ix_fault_predictions_vehicle_id', table_name='fault_predictions')
    op.drop_table('fault_predictions')
    
    op.drop_index('ix_telemetry_readings_vehicle_id_timestamp', table_name='telemetry_readings')
    op.drop_index('ix_telemetry_readings_timestamp', table_name='telemetry_readings')
    op.drop_index('ix_telemetry_readings_vehicle_id', table_name='telemetry_readings')
    op.drop_table('telemetry_readings')
    
    op.drop_index('ix_vehicles_vehicle_id', table_name='vehicles')
    op.drop_table('vehicles')
