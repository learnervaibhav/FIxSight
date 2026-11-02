"""Model loading utilities.

Loads ML artifacts once and exposes them to the app lifecycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import xgboost as xgb


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_MODELS_DIR = PROJECT_ROOT / "ml_models"
FAULT_MODEL_PATH = ML_MODELS_DIR / "xgb_fault_classifier.json"
FAULT_LABEL_ENCODER_PATH = ML_MODELS_DIR / "xgb_fault_classifier_label_encoder.joblib"
RUL_MODEL_PATH = ML_MODELS_DIR / "xgb_rul_forecaster.joblib"


@dataclass(frozen=True)
class ModelRegistry:
	fault_model: xgb.Booster
	fault_feature_names: tuple[str, ...]
	# Index -> human-readable label. Empty when the encoder artifact is missing.
	fault_labels: tuple[str, ...]
	# sklearn-style XGBRegressor, or None when the artifact is missing.
	rul_model: Any | None
	rul_feature_names: tuple[str, ...]


def _load_fault_model() -> xgb.Booster:
	if not FAULT_MODEL_PATH.exists():
		raise FileNotFoundError(f"Fault model not found at: {FAULT_MODEL_PATH}")

	booster = xgb.Booster()
	booster.load_model(str(FAULT_MODEL_PATH))
	return booster


def _load_fault_labels() -> tuple[str, ...]:
	if not FAULT_LABEL_ENCODER_PATH.exists():
		logger.warning("Label encoder not found at %s; using fault_<idx> labels", FAULT_LABEL_ENCODER_PATH)
		return ()
	encoder = joblib.load(FAULT_LABEL_ENCODER_PATH)
	return tuple(str(label) for label in encoder.classes_)


def _load_rul_model() -> tuple[Any | None, tuple[str, ...]]:
	if not RUL_MODEL_PATH.exists():
		logger.warning("RUL model not found at %s; using rule-based RUL", RUL_MODEL_PATH)
		return None, ()
	model = joblib.load(RUL_MODEL_PATH)
	names = tuple(model.get_booster().feature_names or ())
	return model, names


@lru_cache(maxsize=1)
def load_models() -> ModelRegistry:
	"""Load all available models once and cache them."""
	fault_model = _load_fault_model()
	rul_model, rul_feature_names = _load_rul_model()
	return ModelRegistry(
		fault_model=fault_model,
		fault_feature_names=tuple(fault_model.feature_names or ()),
		fault_labels=_load_fault_labels(),
		rul_model=rul_model,
		rul_feature_names=rul_feature_names,
	)


def warmup_models() -> None:
	"""Preload model artifacts during app startup."""
	load_models()
