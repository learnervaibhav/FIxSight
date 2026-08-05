"""Model loading utilities.

Loads ML artifacts once and exposes them to the app lifecycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import xgboost as xgb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_MODELS_DIR = PROJECT_ROOT / "ml_models"
FAULT_MODEL_PATH = ML_MODELS_DIR / "xgb_fault_classifier.json"


@dataclass(frozen=True)
class ModelRegistry:
	fault_model: xgb.Booster
	fault_feature_names: tuple[str, ...]


def _load_fault_model() -> xgb.Booster:
	if not FAULT_MODEL_PATH.exists():
		raise FileNotFoundError(f"Fault model not found at: {FAULT_MODEL_PATH}")

	booster = xgb.Booster()
	booster.load_model(str(FAULT_MODEL_PATH))
	return booster


@lru_cache(maxsize=1)
def load_models() -> ModelRegistry:
	"""Load all available models once and cache them."""
	fault_model = _load_fault_model()
	feature_names = tuple(fault_model.feature_names or ())
	return ModelRegistry(fault_model=fault_model, fault_feature_names=feature_names)


def warmup_models() -> None:
	"""Preload model artifacts during app startup."""
	load_models()

