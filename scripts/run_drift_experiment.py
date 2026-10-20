"""
scripts/run_drift_experiment.py

Synthetic Injected Drift for Pipeline Validation.

Simulates macroeconomic stress/delinquency shifts on the credit benchmark dataset
via controlled feature perturbation, computes Population Stability Index (PSI) per feature,
and validates the drift detection pipeline.

Methodology Note on Real Temporal Drift vs. Partitioning:
In the UCI Default of Credit Card Clients dataset, rows represent individual borrowers
observed cross-sectionally in September 2005. The PAY_0 through PAY_6 columns represent
retrospective repayment histories of those same borrowers, not chronological arrival batches.
Partitioning borrower rows by PAY month values is methodologically invalid because it
confuses intra-individual retrospective features with population observation epochs.
True temporal drift requires distinct calendar tranches; for offline pipeline validation,
controlled synthetic perturbation with seeded pseudorandom distributions is employed.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from backend.app.services.monitoring.engine import MonitoringEngine

PROCESSED_DATA_PATH = REPO_ROOT / "data" / "processed" / "credit_default_cleaned.csv"


def run_synthetic_drift_experiment():
    if not PROCESSED_DATA_PATH.exists():
        print(f"Error: {PROCESSED_DATA_PATH} not found. Run ml/train.py first.")
        return

    df = pd.read_csv(PROCESSED_DATA_PATH)
    
    # Deterministic seeding for exact reproducibility
    np.random.seed(42)

    # Reference distribution: 10,000 random baseline borrower profiles
    ref_df = df.sample(n=10000, random_state=42).copy()

    # Synthetic Drifting distribution (simulated macro-stress):
    # 1. Delinquency inflation: PAY_0 shifted upwards (+0, +1, +2 months delinquency)
    # 2. Credit line contraction: LIMIT_BAL compressed by 10%-40%
    drift_df = df.sample(n=10000, random_state=123).copy()
    drift_df["PAY_0"] = drift_df["PAY_0"] + np.random.choice([0, 1, 2], size=len(drift_df), p=[0.4, 0.4, 0.2])
    drift_df["LIMIT_BAL"] = drift_df["LIMIT_BAL"] * np.random.uniform(0.6, 0.9, size=len(drift_df))

    result = MonitoringEngine.evaluate_batch_drift(
        model_version_id="synthetic_test_model",
        reference_df=ref_df,
        current_df=drift_df,
        reference_batch_id="baseline_sample",
        current_batch_id="adverse_macro_stress_batch",
        drift_source="synthetic injected drift for pipeline validation"
    )

    print("=" * 75)
    print("RiskWise Feature Drift Experiment Results")
    print(f"Drift Source: {result.drift_source}")
    print("=" * 75)
    print(f"Overall Status: {result.overall_status} (Mean PSI: {result.overall_psi:.4f})")
    print("-" * 75)
    print(f"{'Feature':<16} | {'PSI Value':<10} | {'Drift Status':<18}")
    print("-" * 75)
    for feat in result.features:
        if feat.drift_status != "STABLE":
            print(f"{feat.feature_name:<16} | {feat.psi_value:<10.4f} | {feat.drift_status:<18}")

    print("=" * 75)


if __name__ == "__main__":
    run_synthetic_drift_experiment()
