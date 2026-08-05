"""Inference helpers for fault prediction and RUL estimation."""

from __future__ import annotations

from typing import Any

import numpy as np
import xgboost as xgb

from app.ml.feature_engineering import build_feature_frame
from app.ml.model_loader import load_models


def _clamp(value: float, low: float, high: float) -> float:
	return max(low, min(high, value))


def predict_fault(row: dict[str, Any]) -> dict[str, Any]:
	"""Predict fault class and confidence from a single telemetry row."""
	registry = load_models()
	frame = build_feature_frame(row, registry.fault_feature_names)
	matrix = xgb.DMatrix(frame, feature_names=frame.columns.tolist())
	raw_pred = registry.fault_model.predict(matrix)

	if raw_pred.ndim == 2:
		# Multi-class: shape (n_rows, n_classes)
		probs = raw_pred[0]
		class_idx = int(np.argmax(probs))
		confidence = float(probs[class_idx])
	else:
		# Binary/regression-like output. Use threshold for a class label.
		score = float(raw_pred[0])
		class_idx = 1 if score >= 0.5 else 0
		confidence = score if class_idx == 1 else 1.0 - score

	return {
		"fault_class_id": class_idx,
		"fault_label": f"fault_{class_idx}",
		"fault_probability": round(_clamp(confidence, 0.0, 1.0), 4),
	}


def estimate_rul_hourly(
	row: dict[str, Any],
	previous_rul_hours: float | None = None,
	hours_elapsed: float = 1.0,
) -> dict[str, Any]:
	"""Rule-based RUL estimate when no trained RUL model is available.

	Designed for one-row-at-a-time telemetry. Call this once per hour reading.
	"""
	health = _clamp(float(row.get("health_score", 100.0)), 0.0, 100.0)
	degradation = _clamp(float(row.get("degradation_index", 0.0)), 0.0, 1.0)
	engine_load = _clamp(float(row.get("engine_load", 0.0)) / 100.0, 0.0, 1.0)
	coolant_temp = float(row.get("coolant_temperature", 85.0))
	oil_slope = abs(float(row.get("rolling_slope_oil_pressure", 0.0)))

	# Normalize stress factors.
	temp_stress = _clamp((coolant_temp - 90.0) / 40.0, 0.0, 1.0)
	pressure_stress = _clamp(oil_slope / 1.5, 0.0, 1.0)
	health_stress = 1.0 - (health / 100.0)

	# Combined wear rate per hour in [0.02, 0.95].
	wear_rate = _clamp(
		(0.40 * degradation)
		+ (0.25 * health_stress)
		+ (0.20 * engine_load)
		+ (0.10 * temp_stress)
		+ (0.05 * pressure_stress),
		0.02,
		0.95,
	)

	if previous_rul_hours is None:
		# Initial estimate from current health/degradation only.
		baseline_hours = 2400.0
		initial_factor = _clamp((1.0 - degradation) * (health / 100.0), 0.05, 1.0)
		rul_hours = baseline_hours * initial_factor
	else:
		# Decrease RUL every reading period (default: hourly).
		consumption = (6.0 + (24.0 * wear_rate)) * max(hours_elapsed, 0.1)
		rul_hours = max(0.0, float(previous_rul_hours) - consumption)

	confidence = _clamp(0.55 + (0.35 * (1.0 - abs(wear_rate - 0.45))), 0.5, 0.9)

	return {
		"rul_hours": round(rul_hours, 2),
		"rul_confidence": round(confidence, 4),
		"wear_rate": round(wear_rate, 4),
		"update_interval_hours": hours_elapsed,
	}

