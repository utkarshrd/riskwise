#!/usr/bin/env python3
"""
scripts/audit_fairness.py

Performs demographic parity and fair lending audits on the RiskWise champion credit model.
Evaluates AUC, approval rate, empirical default rate, and default recall across:
- SEX (Male vs Female)
- EDUCATION (Graduate School, University, High School, Others)
- MARRIAGE (Married, Single, Others)
- AGE BANDS (<25, 25-34, 35-49, 50+)

Computes Disparate Impact Ratios (DIR) per the EEOC / CFPB Four-Fifths (80%) Rule.
Outputs results to artifacts/evaluation/fairness_audit.json.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ml.data_validation import TARGET_COL
from ml.preprocessing import engineer_features

PROCESSED_DATA_PATH = REPO_ROOT / "data" / "processed" / "credit_default_cleaned.csv"
MODEL_PATH = REPO_ROOT / "artifacts" / "models" / "credit_xgboost_v1.joblib"
PREP_PATH = REPO_ROOT / "artifacts" / "models" / "credit_xgboost_v1_preprocessor.joblib"
EVAL_FILE = REPO_ROOT / "artifacts" / "evaluation" / "model_comparison.json"
AUDIT_OUTPUT_FILE = REPO_ROOT / "artifacts" / "evaluation" / "fairness_audit.json"


def categorize_education(val: int | float) -> str:
    if val == 1:
        return "Graduate School"
    if val == 2:
        return "University"
    if val == 3:
        return "High School"
    return "Others"


def categorize_marriage(val: int | float) -> str:
    if val == 1:
        return "Married"
    if val == 2:
        return "Single"
    return "Others"


def categorize_age(val: int | float) -> str:
    if val < 25:
        return "<25"
    if val <= 34:
        return "25-34"
    if val <= 49:
        return "35-49"
    return "50+"


def compute_group_metrics(df_sub: pd.DataFrame, y_true: np.ndarray, y_prob: np.ndarray, y_pred: np.ndarray) -> dict:
    size = len(y_true)
    if size == 0:
        return {"sample_size": 0, "auc": 0.0, "approval_rate": 0.0, "default_rate": 0.0, "recall": 0.0}

    # Approval rate = fraction approved (predicted non-default: y_pred == 0)
    approval_rate = float(np.mean(y_pred == 0))
    default_rate = float(np.mean(y_true))

    try:
        auc = float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.5
    except Exception:
        auc = 0.5

    recall = float(recall_score(y_true, y_pred, zero_division=0))

    return {
        "sample_size": size,
        "auc": round(auc, 4),
        "approval_rate": round(approval_rate, 4),
        "default_rate": round(default_rate, 4),
        "recall": round(recall, 4)
    }


def run_fairness_audit():
    print("=" * 70)
    print("Running RiskWise Demographic & Fair Lending Audit...")
    print("=" * 70)

    if not PROCESSED_DATA_PATH.exists():
        raise FileNotFoundError(f"Cleaned benchmark dataset not found at {PROCESSED_DATA_PATH}")
    if not MODEL_PATH.exists() or not PREP_PATH.exists():
        raise FileNotFoundError("Model or preprocessor artifact not found in artifacts/models/")

    # 1. Load Cleaned Dataset & Split
    df = pd.read_csv(PROCESSED_DATA_PATH)
    y = df[TARGET_COL].values

    _, temp_idx = train_test_split(df.index, test_size=0.30, random_state=42, stratify=y)
    _, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=42, stratify=y[temp_idx])
    df_test = df.loc[test_idx].copy()
    y_test = df_test[TARGET_COL].values

    # 2. Load Model, Preprocessor, and Threshold
    model = joblib.load(MODEL_PATH)
    preprocessor = joblib.load(PREP_PATH)

    threshold = 0.26
    if EVAL_FILE.exists():
        with open(EVAL_FILE, "r") as f:
            eval_data = json.load(f)
            threshold = eval_data.get("xgboost", {}).get("decision_threshold", 0.26)

    # 3. Predict on Test Set
    df_eng = engineer_features(df_test, include_protected=False)
    X_test_scaled = preprocessor.transform(df_eng)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    # 4. Group Audits
    # (a) Sex
    sex_metrics = {
        "Male (SEX=1)": compute_group_metrics(
            df_test[df_test["SEX"] == 1],
            y_test[df_test["SEX"] == 1],
            y_prob[df_test["SEX"] == 1],
            y_pred[df_test["SEX"] == 1]
        ),
        "Female (SEX=2)": compute_group_metrics(
            df_test[df_test["SEX"] == 2],
            y_test[df_test["SEX"] == 2],
            y_prob[df_test["SEX"] == 2],
            y_pred[df_test["SEX"] == 2]
        )
    }

    # (b) Education
    edu_cats = df_test["EDUCATION"].apply(categorize_education)
    education_metrics = {}
    for cat in ["Graduate School", "University", "High School", "Others"]:
        mask = (edu_cats == cat)
        education_metrics[cat] = compute_group_metrics(df_test[mask], y_test[mask], y_prob[mask], y_pred[mask])

    # (c) Marriage
    marr_cats = df_test["MARRIAGE"].apply(categorize_marriage)
    marriage_metrics = {}
    for cat in ["Married", "Single", "Others"]:
        mask = (marr_cats == cat)
        marriage_metrics[cat] = compute_group_metrics(df_test[mask], y_test[mask], y_prob[mask], y_pred[mask])

    # (d) Age Bands
    age_cats = df_test["AGE"].apply(categorize_age)
    age_metrics = {}
    for cat in ["<25", "25-34", "35-49", "50+"]:
        mask = (age_cats == cat)
        age_metrics[cat] = compute_group_metrics(df_test[mask], y_test[mask], y_prob[mask], y_pred[mask])

    # 5. Compute Disparate Impact Ratios (DIR)
    # DIR = approval_rate(unprivileged) / approval_rate(privileged)
    male_app = sex_metrics["Male (SEX=1)"]["approval_rate"]
    female_app = sex_metrics["Female (SEX=2)"]["approval_rate"]
    sex_dir = round(female_app / male_app, 4) if male_app > 0 else 1.0

    grad_app = education_metrics["Graduate School"]["approval_rate"]
    hs_app = education_metrics["High School"]["approval_rate"]
    education_dir = round(hs_app / grad_app, 4) if grad_app > 0 else 1.0

    married_app = marriage_metrics["Married"]["approval_rate"]
    single_app = marriage_metrics["Single"]["approval_rate"]
    marriage_dir = round(single_app / married_app, 4) if married_app > 0 else 1.0

    ref_age_app = age_metrics["25-34"]["approval_rate"]
    min_age_app = min(m["approval_rate"] for m in age_metrics.values())
    age_dir = round(min_age_app / ref_age_app, 4) if ref_age_app > 0 else 1.0

    all_dirs = [sex_dir, education_dir, marriage_dir, age_dir]
    four_fifths_rule_passed = all(d >= 0.80 for d in all_dirs)

    audit_result = {
        "audit_timestamp": datetime.now(UTC).isoformat(),
        "model_version": "credit_xgboost_v1",
        "feature_set": "engineered_without_protected_attributes",
        "decision_threshold": threshold,
        "sample_size": len(df_test),
        "overall_approval_rate": round(float(np.mean(y_pred == 0)), 4),
        "subgroup_metrics": {
            "sex": sex_metrics,
            "education": education_metrics,
            "marriage": marriage_metrics,
            "age_band": age_metrics
        },
        "disparate_impact_ratios": {
            "sex_female_vs_male": sex_dir,
            "education_highschool_vs_gradschool": education_dir,
            "marriage_single_vs_married": marriage_dir,
            "age_min_vs_reference_25_34": age_dir,
            "four_fifths_rule_threshold": 0.80,
            "four_fifths_rule_compliant": four_fifths_rule_passed
        },
        "fairness_summary": (
            f"Four-fifths fair lending rule compliant: {four_fifths_rule_passed}. "
            f"Sex DIR = {sex_dir:.2f}, Education DIR = {education_dir:.2f}, "
            f"Marriage DIR = {marriage_dir:.2f}, Age DIR = {age_dir:.2f}."
        )
    }

    AUDIT_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(audit_result, f, indent=2)

    print(f"Fairness audit complete. Results saved to {AUDIT_OUTPUT_FILE}")
    print(f"Summary: {audit_result['fairness_summary']}")
    return audit_result


if __name__ == "__main__":
    run_fairness_audit()
