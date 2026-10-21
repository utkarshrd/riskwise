#!/usr/bin/env python3
"""
scripts/audit_fairness.py

Performs demographic parity and fair lending audits on the RiskWise Indian Credit Champion Model.
Evaluates multiclass/tier metrics, approval rates, and adverse impact across:
- GENDER (Male vs Female)
- MARITALSTATUS (Married vs Single)
- EDUCATION (Graduate, Post-Graduate, 12th, SSC, Professional, Under Graduate, Others)
- AGE BANDS (<25, 25-34, 35-49, 50+)

Computes Disparate Impact Ratios (DIR) per the EEOC / CFPB Four-Fifths (80%) Rule.
Approval is defined as predicting Tier P1 or P2 (prime / near-prime).
Outputs results to artifacts/evaluation/fairness_audit.json.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ml.data_validation import TARGET_COL

PROCESSED_DATA_PATH = REPO_ROOT / "data" / "processed" / "credit_indian_cleaned.csv"
MODEL_PATH = REPO_ROOT / "artifacts" / "models" / "credit_xgboost_v1.joblib"
PREP_PATH = REPO_ROOT / "artifacts" / "models" / "credit_xgboost_v1_preprocessor.joblib"
EVAL_FILE = REPO_ROOT / "artifacts" / "evaluation" / "model_comparison.json"
AUDIT_OUTPUT_FILE = REPO_ROOT / "artifacts" / "evaluation" / "fairness_audit.json"

REV_TARGET_MAP = {0: "P1", 1: "P2", 2: "P3", 3: "P4"}
TARGET_MAP = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}


def categorize_age(val: int | float) -> str:
    if pd.isna(val):
        return "Unknown"
    if val < 25:
        return "<25"
    if val <= 34:
        return "25-34"
    if val <= 49:
        return "35-49"
    return "50+"


def compute_group_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    size = len(y_true)
    if size == 0:
        return {
            "sample_size": 0,
            "accuracy": 0.0,
            "macro_f1": 0.0,
            "approval_rate": 0.0,
            "empirical_approval_rate": 0.0,
            "high_risk_rate": 0.0,
        }

    # Approval defined as class P1 or P2 (labels 0 or 1)
    approved_pred = np.isin(y_pred, [0, 1])
    approved_true = np.isin(y_true, [0, 1])

    approval_rate = float(np.mean(approved_pred))
    empirical_approval = float(np.mean(approved_true))
    high_risk_rate = float(np.mean(np.isin(y_pred, [2, 3])))

    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    return {
        "sample_size": size,
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "approval_rate": round(approval_rate, 4),
        "empirical_approval_rate": round(empirical_approval, 4),
        "high_risk_rate": round(high_risk_rate, 4),
    }


def run_fairness_audit():
    print("=" * 70)
    print("Running RiskWise Demographic & Fair Lending Audit on Indian Credit Model...")
    print("=" * 70)

    if not PROCESSED_DATA_PATH.exists():
        raise FileNotFoundError(f"Cleaned Indian credit dataset not found at {PROCESSED_DATA_PATH}")
    if not MODEL_PATH.exists() or not PREP_PATH.exists():
        raise FileNotFoundError("Model or preprocessor artifact not found in artifacts/models/")

    # 1. Load Cleaned Dataset & Split
    df = pd.read_csv(PROCESSED_DATA_PATH)
    y_raw = df[TARGET_COL].values
    y = np.array([TARGET_MAP[val] for val in y_raw])

    _, temp_idx = train_test_split(df.index, test_size=0.30, random_state=42, stratify=y)
    _, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=42, stratify=y[temp_idx])
    df_test = df.loc[test_idx].copy()
    y_test = y[test_idx]

    # 2. Load Model and Preprocessor
    model = joblib.load(MODEL_PATH)
    preprocessor = joblib.load(PREP_PATH)

    # 3. Predict on Test Set
    X_test_trans = preprocessor.transform(df_test)
    y_pred = model.predict(X_test_trans)

    # 4. Group Audits
    # (a) Gender
    gender_metrics = {}
    for g, label in [("M", "Male (M)"), ("F", "Female (F)")]:
        mask = (df_test["GENDER"] == g).values
        gender_metrics[label] = compute_group_metrics(y_test[mask], y_pred[mask])

    # (b) Marital Status
    marital_metrics = {}
    for m in ["Married", "Single"]:
        mask = (df_test["MARITALSTATUS"] == m).values
        marital_metrics[m] = compute_group_metrics(y_test[mask], y_pred[mask])

    # (c) Education
    education_metrics = {}
    for edu in ["GRADUATE", "POST-GRADUATE", "12TH", "SSC", "UNDER GRADUATE", "PROFESSIONAL", "OTHERS"]:
        mask = (df_test["EDUCATION"] == edu).values
        if mask.sum() > 0:
            education_metrics[edu] = compute_group_metrics(y_test[mask], y_pred[mask])

    # (d) Age Bands
    df_test["age_band"] = df_test["AGE"].apply(categorize_age)
    age_metrics = {}
    for band in ["<25", "25-34", "35-49", "50+"]:
        mask = (df_test["age_band"] == band).values
        if mask.sum() > 0:
            age_metrics[band] = compute_group_metrics(y_test[mask], y_pred[mask])

    # 5. Compute Disparate Impact Ratios (DIR)
    # DIR = approval_rate(unprivileged) / approval_rate(privileged)
    male_app = gender_metrics.get("Male (M)", {}).get("approval_rate", 1.0)
    female_app = gender_metrics.get("Female (F)", {}).get("approval_rate", 1.0)
    gender_dir = round(female_app / male_app, 4) if male_app > 0 else 1.0

    grad_app = education_metrics.get("GRADUATE", {}).get("approval_rate", 1.0)
    ssc_app = education_metrics.get("SSC", {}).get("approval_rate", 1.0)
    education_dir = round(ssc_app / grad_app, 4) if grad_app > 0 else 1.0

    married_app = marital_metrics.get("Married", {}).get("approval_rate", 1.0)
    single_app = marital_metrics.get("Single", {}).get("approval_rate", 1.0)
    marital_dir = round(single_app / married_app, 4) if married_app > 0 else 1.0

    ref_age_app = age_metrics.get("25-34", {}).get("approval_rate", 1.0)
    min_age_app = min(m["approval_rate"] for m in age_metrics.values()) if age_metrics else 1.0
    age_dir = round(min_age_app / ref_age_app, 4) if ref_age_app > 0 else 1.0

    all_dirs = [gender_dir, education_dir, marital_dir, age_dir]
    four_fifths_rule_passed = all(d >= 0.80 for d in all_dirs)

    overall_app = float(np.mean(np.isin(y_pred, [0, 1])))

    audit_result = {
        "audit_timestamp": datetime.now(UTC).isoformat(),
        "model_version": "credit_xgboost_v1",
        "dataset_name": "Indian_Banking_CIBIL_Merged_2026",
        "sample_size": len(df_test),
        "overall_approval_rate": round(overall_app, 4),
        "subgroup_metrics": {
            "gender": gender_metrics,
            "marital_status": marital_metrics,
            "education": education_metrics,
            "age_band": age_metrics,
        },
        "disparate_impact_ratios": {
            "gender_female_vs_male": gender_dir,
            "education_ssc_vs_graduate": education_dir,
            "marital_single_vs_married": marital_dir,
            "age_min_vs_reference_25_34": age_dir,
            "four_fifths_rule_threshold": 0.80,
            "four_fifths_rule_compliant": four_fifths_rule_passed,
        },
        "fairness_summary": (
            f"Four-fifths fair lending rule compliant: {four_fifths_rule_passed}. "
            f"Gender DIR = {gender_dir:.2f}, Education DIR = {education_dir:.2f}, "
            f"Marital DIR = {marital_dir:.2f}, Age DIR = {age_dir:.2f}."
        ),
    }

    AUDIT_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(audit_result, f, indent=2)

    print(f"Fairness audit complete. Results saved to {AUDIT_OUTPUT_FILE}")
    print(f"Summary: {audit_result['fairness_summary']}")
    return audit_result


if __name__ == "__main__":
    run_fairness_audit()
