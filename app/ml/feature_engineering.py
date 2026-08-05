"""Feature engineering for single-row inference."""

from __future__ import annotations

from typing import Any

import pandas as pd


DEFAULT_FEATURE_ORDER = [
	"engine_rpm",
	"engine_load",
	"coolant_temperature",
	"oil_temperature",
	"oil_pressure",
	"fuel_rate",
	"short_term_fuel_trim",
	"long_term_fuel_trim",
	"mass_air_flow",
	"intake_manifold_pressure",
	"battery_voltage",
	"alternator_voltage",
	"gear_position",
	"transmission_temperature",
	"o2_sensor_voltage",
	"egr_position",
	"vehicle_speed",
	"throttle_position",
	"cumulative_engine_hours",
	"rolling_mean_temp",
	"rolling_std_temp",
	"rolling_slope_oil_pressure",
	"harsh_acceleration_count",
	"idle_time_ratio",
	"degradation_index",
	"health_score",
]


def _to_float(value: Any, default: float = 0.0) -> float:
	if value is None:
		return default
	try:
		return float(value)
	except (TypeError, ValueError):
		return default


def build_feature_frame(row: dict[str, Any], feature_names: tuple[str, ...] | None = None) -> pd.DataFrame:
	"""Create an ordered one-row DataFrame matching model feature order."""
	ordered = list(feature_names) if feature_names else list(DEFAULT_FEATURE_ORDER)
	data = {name: _to_float(row.get(name, 0.0)) for name in ordered}
	return pd.DataFrame([data], columns=ordered)

