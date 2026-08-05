"""Train FixSight ML models and save them to models/.

Models trained (as specified in how_to_approach_fixsight.txt):
    models/xgb_fault_classifier.json                    -- XGBoost fault type classifier
    models/xgb_fault_classifier_label_encoder.joblib    -- LabelEncoder (required at inference)
    models/xgb_rul_forecaster.joblib                    -- XGBoost RUL regressor

Time-series context is captured through pre-computed rolling window features
already present in telematics_data.csv:
    rolling_mean_temp, rolling_std_temp, rolling_slope_oil_pressure,
    harsh_acceleration_count, idle_time_ratio, degradation_index

This means XGBoost implicitly receives temporal context without needing a
recurrent architecture — consistent with the approach in how_to_approach_fixsight.txt.

Usage:
    python scripts/train_model.py                    # reads dataset/, writes models/
    python scripts/train_model.py --sample 0.1       # fast mode — 10% of rows
    python scripts/train_model.py --no-eval          # skip evaluation output
    python scripts/train_model.py --dataset dataset  # explicit dataset dir
    python scripts/train_model.py --out models       # explicit output dir
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    classification_report,
    mean_absolute_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Feature columns — MUST match TelemetryReading ORM + telematics_data.csv
# ---------------------------------------------------------------------------
FEATURE_COLS = [
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
    # Rolling / engineered time-series features (pre-computed in dataset)
    "rolling_mean_temp",
    "rolling_std_temp",
    "rolling_slope_oil_pressure",
    "harsh_acceleration_count",
    "idle_time_ratio",
    "degradation_index",
]

RUL_TARGET_COL   = "rul_hours"     # continuous  — in telematics_data.csv
FAULT_TARGET_COL = "fault_label"   # categorical — derived from sensor heuristics

# ---------------------------------------------------------------------------
# Fault label strings — MUST match fault_predictions.fault_label in DB exactly.
# Sourced from the live DB snapshot of fault_predictions table.
# ---------------------------------------------------------------------------
FAULT_LABELS = [
    "Coolant overheating",
    "Low oil pressure detected",
    "Battery voltage drop",
    "Transmission overheat",
    "Abnormal fuel trim drift",
    "EGR valve stuck open",
    "Mass air flow sensor fault",
    "Engine misfire detected",
    "Fuel injector fault",
    "normal",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train FixSight XGBoost models")
    p.add_argument("--dataset",    default="dataset", help="Dataset directory (default: dataset/)")
    p.add_argument("--out",        default="models",  help="Output directory for models (default: models/)")
    p.add_argument(
        "--sample", type=float, default=1.0,
        help="Fraction of telemetry rows to use (0 < value <= 1, default: 1.0). "
             "Use --sample 0.1 for fast iteration.",
    )
    p.add_argument("--test-size",  type=float, default=0.2, help="Held-out fraction for evaluation (default: 0.2)")
    p.add_argument("--seed",       type=int,   default=42,  help="Random seed (default: 42)")
    p.add_argument("--no-eval",    action="store_true",     help="Skip evaluation metrics printout")
    return p.parse_args()


def resolve_dir(path_str: str, must_exist: bool = True) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    return path


# ---------------------------------------------------------------------------
# Sensor-based fault label derivation
#
# Each rule maps directly to a fault_label string that exists in the live
# fault_predictions table (observed in DB snapshot):
#
#   "Coolant overheating"      → coolant_temperature  > 110  OR oil_temperature > 130
#   "Low oil pressure detected" → oil_pressure         < 25
#   "Battery voltage drop"      → battery_voltage       < 11.5
#   "Transmission overheat"     → transmission_temperature > 120 AND gear_position >= 3
#   "Abnormal fuel trim drift"  → |short_term_fuel_trim| > 20
#   "EGR valve stuck open"      → egr_position > 80
#   "Mass air flow sensor fault"→ mass_air_flow < 8 AND engine_rpm > 1000
#   "Engine misfire detected"   → degradation_index > 0.8 AND engine_rpm < 800
#   "Fuel injector fault"       → fuel_rate > 28 AND engine_load > 85
#   "normal"                    → all other rows
# ---------------------------------------------------------------------------

def _derive_fault_label(df: pd.DataFrame, seed: int) -> pd.Series:
    rng_  = np.random.default_rng(seed)
    n     = len(df)
    labels = pd.Series(["normal"] * n, index=df.index, dtype=str)

    cond_coolant  = (df["coolant_temperature"] > 110) | (df["oil_temperature"] > 130)
    cond_oil_pres = df["oil_pressure"] < 25
    cond_battery  = df["battery_voltage"] < 11.5
    cond_trans    = (df["transmission_temperature"] > 120) & (df["gear_position"] >= 3)
    cond_fueltrim = df["short_term_fuel_trim"].abs() > 20
    cond_egr      = df["egr_position"] > 80
    cond_maf      = (df["mass_air_flow"] < 8) & (df["engine_rpm"] > 1000)
    cond_misfire  = (df["degradation_index"] > 0.8) & (df["engine_rpm"] < 800)
    cond_injector = (df["fuel_rate"] > 28) & (df["engine_load"] > 85)

    # Apply in priority order (most safety-critical first)
    labels[cond_coolant]                                                      = "Coolant overheating"
    labels[cond_oil_pres  & ~cond_coolant]                                    = "Low oil pressure detected"
    labels[cond_battery   & ~cond_coolant & ~cond_oil_pres]                   = "Battery voltage drop"
    labels[cond_trans     & ~cond_coolant & ~cond_oil_pres & ~cond_battery]   = "Transmission overheat"
    labels[cond_fueltrim  & (labels == "normal")]                              = "Abnormal fuel trim drift"
    labels[cond_egr       & (labels == "normal")]                              = "EGR valve stuck open"
    labels[cond_maf       & (labels == "normal")]                              = "Mass air flow sensor fault"
    labels[cond_misfire   & (labels == "normal")]                              = "Engine misfire detected"
    labels[cond_injector  & (labels == "normal")]                              = "Fuel injector fault"

    # Add ~2% noise to normal rows so the model doesn't learn a hard boundary
    normal_mask   = labels == "normal"
    noise_mask    = normal_mask & (rng_.random(n) < 0.02)
    minority      = [lbl for lbl in FAULT_LABELS if lbl != "normal"]
    labels[noise_mask] = rng_.choice(minority, size=int(noise_mask.sum()))

    return labels


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_and_prepare(dataset_dir: Path, sample_frac: float, seed: int) -> pd.DataFrame:
    telem_csv = dataset_dir / "telematics_data.csv"
    if not telem_csv.exists():
        raise FileNotFoundError(
            f"telematics_data.csv not found at {telem_csv}\n"
            f"Run:  python scripts/generate_dataset.py"
        )

    print(f"Loading {telem_csv} …")
    df = pd.read_csv(telem_csv, usecols=FEATURE_COLS + [RUL_TARGET_COL])
    print(f"  Loaded {len(df):,} rows  ×  {len(df.columns)} columns")

    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"telematics_data.csv missing columns: {missing}")

    df = df.dropna()
    print(f"  After dropna: {len(df):,} rows")

    if sample_frac < 1.0:
        df = df.sample(frac=sample_frac, random_state=seed).reset_index(drop=True)
        print(f"  Sampled {sample_frac:.0%}: {len(df):,} rows")

    print("  Deriving fault labels from sensor rules …")
    df[FAULT_TARGET_COL] = _derive_fault_label(df, seed)

    label_counts = df[FAULT_TARGET_COL].value_counts()
    print("  Fault label distribution:")
    for lbl, cnt in label_counts.items():
        print(f"    {lbl:<35}: {cnt:>8,}  ({cnt / len(df):.1%})")
    print()

    return df


# ---------------------------------------------------------------------------
# Model 1 — Fault Classifier  →  models/xgb_fault_classifier.json
# ---------------------------------------------------------------------------

def train_fault_classifier(
    df:        pd.DataFrame,
    out_dir:   Path,
    test_size: float,
    seed:      int,
    do_eval:   bool,
) -> None:
    print("=" * 60)
    print("Training fault classifier  →  xgb_fault_classifier.json")
    print("=" * 60)

    X     = df[FEATURE_COLS].astype(float)
    y_raw = df[FAULT_TARGET_COL]

    # Fit LabelEncoder on the full, fixed FAULT_LABELS list so the encoding
    # is deterministic and consistent regardless of which labels appear in data.
    le = LabelEncoder()
    le.fit(FAULT_LABELS)
    y = le.transform(y_raw)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        objective="multi:softmax",
        num_class=len(le.classes_),
        random_state=seed,
        n_jobs=-1,
        verbosity=0,
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Save model (XGBoost native JSON format)
    clf_path = out_dir / "xgb_fault_classifier.json"
    model.save_model(str(clf_path))
    print(f"  ✓ {clf_path}")

    # Save LabelEncoder — required by app/ml/model_loader.py at inference time
    le_path = out_dir / "xgb_fault_classifier_label_encoder.joblib"
    joblib.dump(le, le_path)
    print(f"  ✓ {le_path}  (LabelEncoder — needed for decoding predictions)")

    if do_eval:
        y_pred = model.predict(X_test)
        print("\n  Classification Report:")
        print(
            classification_report(
                y_test, y_pred,
                target_names=le.classes_,
                zero_division=0,
            )
        )


# ---------------------------------------------------------------------------
# Model 2 — RUL Forecaster  →  models/xgb_rul_forecaster.joblib
# ---------------------------------------------------------------------------

def train_rul_forecaster(
    df:        pd.DataFrame,
    out_dir:   Path,
    test_size: float,
    seed:      int,
    do_eval:   bool,
) -> None:
    print("=" * 60)
    print("Training RUL forecaster  →  xgb_rul_forecaster.joblib")
    print("=" * 60)

    X = df[FEATURE_COLS].astype(float)
    y = df[RUL_TARGET_COL].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )
    print(f"  Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    model = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=8,
        learning_rate=0.04,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=seed,
        n_jobs=-1,
        verbosity=0,
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    rul_path = out_dir / "xgb_rul_forecaster.joblib"
    joblib.dump(model, rul_path)
    print(f"  ✓ {rul_path}")

    if do_eval:
        y_pred = model.predict(X_test)
        print(f"\n  MAE  : {mean_absolute_error(y_test, y_pred):.2f} hours")
        print(f"  R²   : {r2_score(y_test, y_pred):.4f}")
        print(f"  Mean actual RUL   : {y_test.mean():.1f} hours")
        print(f"  Mean predicted RUL: {y_pred.mean():.1f} hours")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args       = parse_args()
    dataset_dir = resolve_dir(args.dataset, must_exist=True)
    out_dir     = resolve_dir(args.out,     must_exist=False)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[train_model] dataset dir : {dataset_dir}")
    print(f"[train_model] output dir  : {out_dir}")
    print(f"[train_model] sample frac : {args.sample:.0%}")
    print(f"[train_model] test size   : {args.test_size:.0%}")
    print(f"[train_model] seed        : {args.seed}")
    print()

    df = load_and_prepare(dataset_dir, args.sample, args.seed)

    train_fault_classifier(df, out_dir, args.test_size, args.seed, not args.no_eval)
    print()
    train_rul_forecaster(df, out_dir, args.test_size, args.seed, not args.no_eval)
    print()

    print("=" * 60)
    print("Training complete. Models saved:")
    print(f"  {out_dir / 'xgb_fault_classifier.json'}")
    print(f"  {out_dir / 'xgb_fault_classifier_label_encoder.joblib'}")
    print(f"  {out_dir / 'xgb_rul_forecaster.joblib'}")
    print()
    print("Next step:  python scripts/seed_database.py")


if __name__ == "__main__":
    main()
