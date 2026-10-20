#!/usr/bin/env python3
"""
scripts/train_indian_credit.py

End-to-End Indian Credit Dataset Training & Evaluation Pipeline for RiskWise
1. Merges External_Cibil_Dataset.xlsx and Internal_Bank_Dataset.xlsx on PROSPECTID.
2. Validates data integrity, sentinels (-99999), and feature distributions.
3. Performs stratified 70/15/15 train/val/test splitting.
4. Trains and evaluates:
   - Majority Class Baseline
   - Multinomial Logistic Regression
   - XGBoost (42 features, NO Credit_Score) [Target Champion]
   - XGBoost (43 features, WITH Credit_Score) [Leakage Study]
5. Computes held-out test metrics: Accuracy, Macro-F1, Weighted-F1, Per-class metrics, Confusion Matrix.
6. Evaluates SHAP explainability.
7. Evaluates on Unseen_Dataset.xlsx.
8. Persists production artifacts and updates evaluation registry.
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "models"
EVAL_DIR = REPO_ROOT / "artifacts" / "evaluation"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)

TARGET_MAP = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
REV_TARGET_MAP = {0: "P1", 1: "P2", 2: "P3", 3: "P4"}
CLASSES = ["P1", "P2", "P3", "P4"]

# 42 Candidate Features matching Unseen Dataset schema
NUMERIC_FEATURES = [
    'pct_tl_open_L6M', 'pct_tl_closed_L6M', 'Tot_TL_closed_L12M', 'pct_tl_closed_L12M',
    'Tot_Missed_Pmnt', 'CC_TL', 'Home_TL', 'PL_TL', 'Secured_TL', 'Unsecured_TL',
    'Other_TL', 'Age_Oldest_TL', 'Age_Newest_TL', 'time_since_recent_payment',
    'max_recent_level_of_deliq', 'num_deliq_6_12mts', 'num_times_60p_dpd',
    'num_std_12mts', 'num_sub', 'num_sub_6mts', 'num_sub_12mts', 'num_dbt',
    'num_dbt_12mts', 'num_lss', 'recent_level_of_deliq', 'CC_enq_L12m', 'PL_enq_L12m',
    'time_since_recent_enq', 'enq_L3m', 'NETMONTHLYINCOME', 'Time_With_Curr_Empr',
    'CC_Flag', 'PL_Flag', 'pct_PL_enq_L6m_of_ever', 'pct_CC_enq_L6m_of_ever',
    'HL_Flag', 'GL_Flag'
]

CATEGORICAL_FEATURES = [
    'MARITALSTATUS', 'EDUCATION', 'GENDER', 'last_prod_enq2', 'first_prod_enq2'
]

CORE_42_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def clean_dataframe(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Replaces sentinel -99999 with np.nan for numeric features."""
    cleaned = df[feature_cols].copy()
    for col in feature_cols:
        if col in NUMERIC_FEATURES or col == "Credit_Score":
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
            cleaned[col] = cleaned[col].replace(-99999, np.nan)
        else:
            cleaned[col] = cleaned[col].astype(str).fillna("Unknown")
    return cleaned


def create_preprocessor(numeric_cols: list[str], categorical_cols: list[str]):
    num_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num", num_pipe, numeric_cols),
        ("cat", cat_pipe, categorical_cols),
    ])


def evaluate_multiclass(y_true, y_pred, y_prob, model_name: str) -> dict:
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2, 3]).tolist()
    
    prec_per_class = precision_score(y_true, y_pred, average=None, labels=[0, 1, 2, 3], zero_division=0)
    rec_per_class = recall_score(y_true, y_pred, average=None, labels=[0, 1, 2, 3], zero_division=0)
    f1_per_class = f1_score(y_true, y_pred, average=None, labels=[0, 1, 2, 3], zero_division=0)

    per_class = {}
    for i, cls in enumerate(CLASSES):
        per_class[cls] = {
            "precision": round(float(prec_per_class[i]), 4),
            "recall": round(float(rec_per_class[i]), 4),
            "f1": round(float(f1_per_class[i]), 4),
            "support": int((y_true == i).sum()),
        }

    try:
        loss = float(log_loss(y_true, y_prob, labels=[0, 1, 2, 3]))
    except Exception:
        loss = None

    return {
        "model_name": model_name,
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "log_loss": round(loss, 4) if loss is not None else None,
        "per_class": per_class,
        "confusion_matrix": cm,
    }


def main():
    print("=" * 80)
    print("RiskWise Indian Credit Risk Model Training & Evaluation")
    print("=" * 80)

    # 1. Load data
    ext_path = DATASET_DIR / "External_Cibil_Dataset.xlsx"
    int_path = DATASET_DIR / "Internal_Bank_Dataset.xlsx"
    unseen_path = DATASET_DIR / "Unseen_Dataset.xlsx"

    print("Loading datasets...")
    df_ext = pd.read_excel(ext_path)
    df_int = pd.read_excel(int_path)
    df_unseen = pd.read_excel(unseen_path)

    print(f"External shape: {df_ext.shape}, Internal shape: {df_int.shape}")
    merged = pd.merge(df_int, df_ext, on="PROSPECTID", how="inner")
    print(f"Merged shape: {merged.shape}")
    assert len(merged) == 51336, "Merge count mismatch!"

    y = merged["Approved_Flag"].map(TARGET_MAP).values
    print("Target distribution:", pd.Series(merged["Approved_Flag"]).value_counts().to_dict())

    # 2. Data splitting: Stratified 70/15/15
    # First split: 70% train, 30% temp
    indices = np.arange(len(merged))
    idx_train, idx_temp, y_train, y_temp = train_test_split(
        indices, y, test_size=0.30, random_state=42, stratify=y
    )
    # Second split: 50/50 of temp -> 15% val, 15% test
    idx_val, idx_test, y_val, y_test = train_test_split(
        idx_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    print(f"Splits: Train={len(idx_train)} (70%), Val={len(idx_val)} (15%), Test={len(idx_test)} (15%)")

    # 3. Prepare Feature Sets
    # Feature Set 1: Core 42 (No Credit_Score)
    X_42 = clean_dataframe(merged, CORE_42_FEATURES)
    X_42_train = X_42.iloc[idx_train]
    X_42_val = X_42.iloc[idx_val]
    X_42_test = X_42.iloc[idx_test]

    # Feature Set 2: Core 42 + Credit_Score (For Leakage Analysis)
    FEATURES_WITH_CS = CORE_42_FEATURES + ["Credit_Score"]
    NUMERIC_WITH_CS = NUMERIC_FEATURES + ["Credit_Score"]
    X_cs = clean_dataframe(merged, FEATURES_WITH_CS)
    X_cs_train = X_cs.iloc[idx_train]
    X_cs_val = X_cs.iloc[idx_val]
    X_cs_test = X_cs.iloc[idx_test]

    # Preprocessors
    prep_42 = create_preprocessor(NUMERIC_FEATURES, CATEGORICAL_FEATURES)
    prep_42.fit(X_42_train)

    X_42_train_trans = prep_42.transform(X_42_train)
    X_42_val_trans = prep_42.transform(X_42_val)
    X_42_test_trans = prep_42.transform(X_42_test)

    prep_cs = create_preprocessor(NUMERIC_WITH_CS, CATEGORICAL_FEATURES)
    prep_cs.fit(X_cs_train)
    X_cs_train_trans = prep_cs.transform(X_cs_train)
    X_cs_val_trans = prep_cs.transform(X_cs_val)
    X_cs_test_trans = prep_cs.transform(X_cs_test)

    results = {}

    # --- MODEL 1: Majority Class Baseline ---
    print("\n--- Training Model 1: Majority Class Baseline ---")
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_42_train_trans, y_train)
    dummy_pred = dummy.predict(X_42_test_trans)
    dummy_prob = dummy.predict_proba(X_42_test_trans)
    results["majority_baseline"] = evaluate_multiclass(y_test, dummy_pred, dummy_prob, "Majority Class Baseline")
    print(f"Majority Baseline Test Macro-F1: {results['majority_baseline']['macro_f1']}, Accuracy: {results['majority_baseline']['accuracy']}")

    # --- MODEL 2: Multinomial Logistic Regression ---
    print("\n--- Training Model 2: Multinomial Logistic Regression (42 features) ---")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_42_train_trans, y_train)
    lr_pred = lr.predict(X_42_test_trans)
    lr_prob = lr.predict_proba(X_42_test_trans)
    results["logistic_regression"] = evaluate_multiclass(y_test, lr_pred, lr_prob, "Multinomial Logistic Regression")
    print(f"Logistic Regression Test Macro-F1: {results['logistic_regression']['macro_f1']}, Accuracy: {results['logistic_regression']['accuracy']}")

    # --- MODEL 3: XGBoost (Core 42 features - NO Credit_Score) ---
    print("\n--- Training Model 3: XGBoost Classifier (Core 42 Features - NO Credit_Score) ---")
    xgb_no_cs = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=4,
        random_state=42,
        eval_metric="mlogloss",
        n_jobs=-1,
    )
    xgb_no_cs.fit(
        X_42_train_trans, y_train,
        eval_set=[(X_42_val_trans, y_val)],
        verbose=False,
    )
    xgb_pred = xgb_no_cs.predict(X_42_test_trans)
    xgb_prob = xgb_no_cs.predict_proba(X_42_test_trans)
    results["xgboost_no_credit_score"] = evaluate_multiclass(y_test, xgb_pred, xgb_prob, "XGBoost (No Credit_Score)")
    print(f"XGBoost (No CS) Test Macro-F1: {results['xgboost_no_credit_score']['macro_f1']}, Accuracy: {results['xgboost_no_credit_score']['accuracy']}")

    # --- MODEL 4: XGBoost (WITH Credit_Score - Leakage Study) ---
    print("\n--- Training Model 4: XGBoost Classifier (WITH Credit_Score - Leakage Study) ---")
    xgb_cs = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=4,
        random_state=42,
        eval_metric="mlogloss",
        n_jobs=-1,
    )
    xgb_cs.fit(
        X_cs_train_trans, y_train,
        eval_set=[(X_cs_val_trans, y_val)],
        verbose=False,
    )
    xgb_cs_pred = xgb_cs.predict(X_cs_test_trans)
    xgb_cs_prob = xgb_cs.predict_proba(X_cs_test_trans)
    results["xgboost_with_credit_score"] = evaluate_multiclass(y_test, xgb_cs_pred, xgb_cs_prob, "XGBoost (With Credit_Score)")
    print(f"XGBoost (With CS) Test Macro-F1: {results['xgboost_with_credit_score']['macro_f1']}, Accuracy: {results['xgboost_with_credit_score']['accuracy']}")

    # --- Leakage Summary ---
    print("\n" + "=" * 80)
    print("LEAKAGE COMPARISON SUMMARY:")
    print(f"XGBoost WITHOUT Credit_Score: Macro-F1 = {results['xgboost_no_credit_score']['macro_f1']}, Accuracy = {results['xgboost_no_credit_score']['accuracy']}")
    print(f"XGBoost WITH Credit_Score:    Macro-F1 = {results['xgboost_with_credit_score']['macro_f1']}, Accuracy = {results['xgboost_with_credit_score']['accuracy']}")
    print("=" * 80)

    # 4. SHAP Explainer for Champion Model (xgb_no_cs)
    print("\nFitting SHAP TreeExplainer for Champion Model...")
    # Use TreeExplainer on a sample background for performance
    explainer = shap.TreeExplainer(xgb_no_cs)
    sample_X = X_42_test_trans[:100]
    sample_shap = explainer.shap_values(sample_X)
    print("SHAP values computed successfully on sample. Shape:", np.shape(sample_shap))

    # Feature names from preprocessor
    cat_names = prep_42.named_transformers_["cat"].named_steps["encoder"].get_feature_names_out(CATEGORICAL_FEATURES).tolist()
    all_feature_names = NUMERIC_FEATURES + cat_names

    # 5. Inference on Unseen Dataset
    print("\nEvaluating on Unseen Dataset (100 rows, 42 features)...")
    unseen_cleaned = clean_dataframe(df_unseen, CORE_42_FEATURES)
    unseen_trans = prep_42.transform(unseen_cleaned)
    unseen_preds = xgb_no_cs.predict(unseen_trans)
    unseen_probs = xgb_no_cs.predict_proba(unseen_trans)

    unseen_records = []
    for i in range(len(df_unseen)):
        pred_label = REV_TARGET_MAP[int(unseen_preds[i])]
        probs = {cls: round(float(unseen_probs[i][j]), 4) for j, cls in enumerate(CLASSES)}
        unseen_records.append({
            "index": i,
            "predicted_category": pred_label,
            "probabilities": probs,
        })
    
    unseen_df = pd.DataFrame(unseen_records)
    print("Unseen Dataset Prediction Distribution:")
    print(unseen_df["predicted_category"].value_counts().to_dict())

    unseen_out_path = EVAL_DIR / "unseen_predictions.json"
    with open(unseen_out_path, "w", encoding="utf-8") as f:
        json.dump(unseen_records, f, indent=2)
    print(f"Saved unseen predictions to {unseen_out_path}")

    # 6. Save Production Artifacts
    print("\nSaving Production Artifacts...")
    version = "credit_indian_xgboost_v1"

    # Save model and preprocessor
    model_path = ARTIFACTS_DIR / f"{version}.joblib"
    prep_path = ARTIFACTS_DIR / f"{version}_preprocessor.joblib"
    explainer_path = ARTIFACTS_DIR / f"{version}_explainer.joblib"

    joblib.dump(xgb_no_cs, model_path)
    joblib.dump({
        "preprocessor": prep_42,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "all_feature_names": all_feature_names,
        "core_features": CORE_42_FEATURES,
        "target_map": TARGET_MAP,
        "rev_target_map": REV_TARGET_MAP,
    }, prep_path)
    joblib.dump(explainer, explainer_path)
    print(f"Saved model to {model_path}")
    print(f"Saved preprocessor to {prep_path}")
    print(f"Saved explainer to {explainer_path}")

    # Also save metadata / evaluation summary
    eval_summary = {
        "model_version": version,
        "dataset_name": "Indian_Banking_CIBIL_Merged_2026",
        "dataset_records": len(merged),
        "target": "Approved_Flag",
        "classes": CLASSES,
        "class_distribution": pd.Series(merged["Approved_Flag"]).value_counts().to_dict(),
        "train_size": len(idx_train),
        "val_size": len(idx_val),
        "test_size": len(idx_test),
        "selected_features_count": len(CORE_42_FEATURES),
        "models_evaluated": results,
        "champion_model": "xgboost_no_credit_score",
        "champion_metrics": results["xgboost_no_credit_score"],
        "leakage_study": {
            "credit_score_included_f1": results["xgboost_with_credit_score"]["macro_f1"],
            "credit_score_excluded_f1": results["xgboost_no_credit_score"]["macro_f1"],
            "rationale": (
                "Credit_Score was intentionally excluded from the champion production model because: "
                "1) Credit_Score was directly used by the lender in tier cutoffs to assign Approved_Flag (target leakage). "
                "2) Credit_Score is completely missing from Unseen_Dataset.xlsx. "
                "3) A true risk model must predict creditworthiness from underlying bureau behavior and credit trade lines."
            )
        },
        "trained_at": datetime.now(UTC).isoformat(),
    }

    eval_json_path = EVAL_DIR / "indian_credit_model_comparison.json"
    with open(eval_json_path, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)
    print(f"Saved evaluation report to {eval_json_path}")

    # Print confusion matrix of champion
    print("\nChampion Model Confusion Matrix (Labels: P1, P2, P3, P4):")
    print(np.array(results["xgboost_no_credit_score"]["confusion_matrix"]))
    print("\nPer-Class Metrics:")
    for cls, met in results["xgboost_no_credit_score"]["per_class"].items():
        print(f"  {cls}: Prec={met['precision']}, Rec={met['recall']}, F1={met['f1']}, Support={met['support']}")

    print("\nTraining & evaluation completed successfully!")


if __name__ == "__main__":
    main()
