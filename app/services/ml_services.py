"""ML service orchestration for API/agent layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ml.inference import predict_fault, predict_rul
from app.models import FaultPrediction, RULPrediction


class MLService:
	"""Thin orchestration over ML inference helpers."""

	@staticmethod
	def derive_severity(probability: float, fault_label: str | None = None) -> str:
		if fault_label == "normal":
			return "LOW"
		if probability >= 0.85:
			return "HIGH"
		if probability >= 0.65:
			return "MEDIUM"
		return "LOW"

	@staticmethod
	def predict_fault(row: dict[str, Any]) -> dict[str, Any]:
		return predict_fault(row)

	@staticmethod
	def predict_rul(
		row: dict[str, Any],
		previous_rul_hours: float | None = None,
		hours_elapsed: float = 1.0,
	) -> dict[str, Any]:
		return predict_rul(
			row,
			previous_rul_hours=previous_rul_hours,
			hours_elapsed=hours_elapsed,
		)

	@staticmethod
	def analyze(
		row: dict[str, Any],
		previous_rul_hours: float | None = None,
		hours_elapsed: float = 1.0,
	) -> dict[str, Any]:
		fault = predict_fault(row)
		rul = predict_rul(
			row,
			previous_rul_hours=previous_rul_hours,
			hours_elapsed=hours_elapsed,
		)
		return {**fault, **rul}

	@staticmethod
	def get_latest_rul_hours(db: Session, vehicle_id: str) -> float | None:
		latest = (
			db.query(RULPrediction)
			.filter(RULPrediction.vehicle_id == vehicle_id)
			.order_by(RULPrediction.created_at.desc(), RULPrediction.id.desc())
			.first()
		)
		return float(latest.rul_hours) if latest else None

	@staticmethod
	def save_fault_prediction(
		db: Session,
		vehicle_id: str,
		telemetry_reading_id: int,
		fault_label: str,
		fault_probability: float,
		llm_explanation: str | None = None,
	) -> FaultPrediction:
		entry = FaultPrediction(
			vehicle_id=vehicle_id,
			telemetry_reading_id=telemetry_reading_id,
			fault_label=fault_label,
			fault_probability=fault_probability,
			severity=MLService.derive_severity(fault_probability, fault_label),
			llm_explanation=llm_explanation,
		)
		db.add(entry)
		db.commit()
		db.refresh(entry)
		return entry

	@staticmethod
	def update_fault_explanation(db: Session, fault_prediction_id: int, explanation: str) -> None:
		entry = db.get(FaultPrediction, fault_prediction_id)
		if entry is None:
			return
		entry.llm_explanation = explanation
		db.commit()

	@staticmethod
	def save_rul_prediction(
		db: Session,
		vehicle_id: str,
		telemetry_reading_id: int,
		rul_hours: float,
		rul_confidence: float,
	) -> RULPrediction:
		entry = RULPrediction(
			vehicle_id=vehicle_id,
			telemetry_reading_id=telemetry_reading_id,
			rul_hours=rul_hours,
			confidence_score=rul_confidence,
		)
		db.add(entry)
		db.commit()
		db.refresh(entry)
		return entry
