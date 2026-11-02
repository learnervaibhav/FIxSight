"""Inference helpers for fault prediction and RUL estimation."""

from __future__ import annotations

from typing import Any

import numpy as np
import xgboost as xgb

from app.ml.feature_engineering import build_feature_frame
from app.ml.model_loader import load_models


NORMAL_LABEL = "normal"


def _clamp(value: float, low: float, high: float) -> float:
	return max(low, min(high, value))


def _softmax(margins: np.ndarray) -> np.ndarray:
	shifted = margins - margins.max()
	exp = np.exp(shifted)
	return exp / exp.sum()


def predict_fault(row: dict[str, Any]) -> dict[str, Any]:
	"""Predict fault class and confidence from a single telemetry row.

	The classifier is trained with ``multi:softmax`` which makes ``predict`` return
	class indices, so raw margins are requested and turned into probabilities here.

	``fault_probability`` is the probability that *some* fault is present:
	the predicted class probability for a fault, or ``1 - p(normal)`` for normal rows.
	"""
	registry = load_models()
	frame = build_feature_frame(row, registry.fault_feature_names)
	matrix = xgb.DMatrix(frame, feature_names=frame.columns.tolist())
	margins = np.asarray(registry.fault_model.predict(matrix, output_margin=True))

	if margins.ndim == 2 and margins.shape[1] > 1:
		probs = _softmax(margins[0])
	else:
		# Binary model: single logit for the positive class.
		positive = float(1.0 / (1.0 + np.exp(-float(margins.reshape(-1)[0]))))
		probs = np.array([1.0 - positive, positive])

	class_idx = int(np.argmax(probs))
	labels = registry.fault_labels
	label = labels[class_idx] if class_idx < len(labels) else f"fault_{class_idx}"
	class_confidence = float(probs[class_idx])

	is_fault = label != NORMAL_LABEL
	if is_fault:
		fault_probability = class_confidence
	else:
		normal_idx = labels.index(NORMAL_LABEL) if NORMAL_LABEL in labels else class_idx
		fault_probability = 1.0 - float(probs[normal_idx])

	return {
		"fault_class_id": class_idx,
		"fault_label": label,
		"fault_probability": round(_clamp(fault_probability, 0.0, 1.0), 4),
		"class_confidence": round(_clamp(class_confidence, 0.0, 1.0), 4),
		"is_fault": is_fault,
	}


def predict_rul(
	row: dict[str, Any],
	previous_rul_hours: float | None = None,
	hours_elapsed: float = 1.0,
) -> dict[str, Any]:
	"""Predict remaining useful life with the trained regressor, falling back to rules."""
	registry = load_models()
	rule_based = estimate_rul_hourly(row, previous_rul_hours=previous_rul_hours, hours_elapsed=hours_elapsed)
	if registry.rul_model is None:
		return {**rule_based, "rul_source": "rule"}

	frame = build_feature_frame(row, registry.rul_feature_names)
	predicted = float(np.asarray(registry.rul_model.predict(frame)).reshape(-1)[0])
	return {
		**rule_based,
		"rul_hours": round(max(0.0, predicted), 2),
		"rul_source": "model",
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
