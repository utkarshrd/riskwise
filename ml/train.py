#!/usr/bin/env python3
"""
ml/train.py

RiskWise Indian Credit Risk Model Training & Evaluation Pipeline
- Merges External_Cibil_Dataset.xlsx and Internal_Bank_Dataset.xlsx on PROSPECTID.
- Stratified 70/15/15 train/val/test split with fixed random seed.
- Fits IndianCreditPreprocessor strictly on training partition.
- Evaluates:
    1. Majority Class Baseline
    2. Multinomial Logistic Regression
    3. XGBoost Multiclass (42 features - NO Credit_Score) [Champion]
    4. XGBoost Multiclass (43 features - WITH Credit_Score) [Leakage Study]
- Fits SHAP TreeExplainer for feature importance.
- Runs inference on Unseen_Dataset.xlsx (100 rows).
- Saves production artifacts to artifacts/models/ and artifacts/evaluation/.
"""

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.config import settings
from backend.app.db.models import AuditEvent, ModelVersion
from backend.app.db.session import SessionLocal
from ml.data_validation import (
    ALLOWED_CATEGORIES,
    CATEGORICAL_FEATURES,
    EXPECTED_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_CLASSES,
    TARGET_COL,
    validate_credit_data,
)
from ml.preprocessing import IndianCreditPreprocessor

DATASET_DIR = REPO_ROOT / "dataset"
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "models"
EVAL_DIR = REPO_ROOT / "artifacts" / "evaluation"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

TARGET_MAP = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
REV_TARGET_MAP = {0: "P1", 1: "P2", 2: "P3", 3: "P4"}


def compute_file_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def evaluate_multiclass(y_true, y_pred, y_prob, model_name: str) -> dict:
    acc = float(accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2, 3]).tolist()
    
    prec_per_class = precision_score(y_true, y_pred, average=None, labels=[0, 1, 2, 3], zero_division=0)
    rec_per_class = recall_score(y_true, y_pred, average=None, labels=[0, 1, 2, 3], zero_division=0)
    f1_per_class = f1_score(y_true, y_pred, average=None, labels=[0, 1, 2, 3], zero_division=0)

    per_class = {}
    for i, cls in enumerate(TARGET_CLASSES):
        per_class[cls] = {
            "precision": round(float(prec_per_class[i]), 4),
            "recall": round(float(rec_per_class[i]), 4),
            "f1": round(float(f1_per_class[i]), 4),
            "support": int((y_true == i).sum()),
        }

    # Multiclass ROC-AUC (One-vs-Rest)
    try:
        roc_auc = float(roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro"))
    except Exception:
        roc_auc = 0.5

    try:
        loss = float(log_loss(y_true, y_prob, labels=[0, 1, 2, 3]))
    except Exception:
        loss = 0.0

    return {
        "model_name": model_name,
        "roc_auc": round(roc_auc, 4),
        "f1_score": round(macro_f1, 4),
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "log_loss": round(loss, 4),
        "decision_threshold": 0.5,
        "risk_band_cutoffs": {
            "low": 0.15,
            "moderate": 0.40,
            "elevated": 0.65
        },
        "per_class": per_class,
        "confusion_matrix": cm,
    }


def train_and_evaluate(auto_register: bool = True) -> dict:
    ext_path = DATASET_DIR / "External_Cibil_Dataset.xlsx"
    int_path = DATASET_DIR / "Internal_Bank_Dataset.xlsx"
    unseen_path = DATASET_DIR / "Unseen_Dataset.xlsx"

    if not ext_path.exists() or not int_path.exists():
        raise FileNotFoundError(f"Source datasets not found in {DATASET_DIR}")

    print("Step 1: Reading Excel datasets...")
    df_ext = pd.read_excel(ext_path)
    df_int = pd.read_excel(int_path)
    print(f"External: {df_ext.shape}, Internal: {df_int.shape}")

    print("Step 2: Merging on PROSPECTID...")
    merged = pd.merge(df_int, df_ext, on="PROSPECTID", how="inner")
    print(f"Merged: {merged.shape}")
    assert len(merged) == 51336, f"Expected 51336 records, got {len(merged)}"

    # Save processed CSV for local inspection & caching
    processed_csv = PROCESSED_DIR / "credit_indian_cleaned.csv"
    merged.to_csv(processed_csv, index=False)
    print(f"Saved processed data to {processed_csv}")

    # Validate data
    is_valid, val_report, clean_merged = validate_credit_data(merged)
    assert is_valid, f"Data validation failed: {val_report.summary}"

    y = clean_merged[TARGET_COL].map(TARGET_MAP).values

    # Stratified 70/15/15 split
    indices = np.arange(len(clean_merged))
    idx_train, idx_temp, y_train, y_temp = train_test_split(
        indices, y, test_size=0.30, random_state=42, stratify=y
    )
    idx_val, idx_test, y_val, y_test = train_test_split(
        idx_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    X_train = clean_merged.iloc[idx_train][EXPECTED_COLUMNS]
    X_val = clean_merged.iloc[idx_val][EXPECTED_COLUMNS]
    X_test = clean_merged.iloc[idx_test][EXPECTED_COLUMNS]

    print(f"Splits: Train={len(X_train)} (70%), Val={len(X_val)} (15%), Test={len(X_test)} (15%)")

    # Fit preprocessor on train only
    preprocessor = IndianCreditPreprocessor()
    preprocessor.fit(X_train)

    X_train_trans = preprocessor.transform(X_train)
    X_val_trans = preprocessor.transform(X_val)
    X_test_trans = preprocessor.transform(X_test)

    eval_results = {}

    # 1. Baseline
    print("Step 3: Training Majority Class Baseline...")
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train_trans, y_train)
    dummy_pred = dummy.predict(X_test_trans)
    dummy_prob = dummy.predict_proba(X_test_trans)
    eval_results["majority_baseline"] = evaluate_multiclass(y_test, dummy_pred, dummy_prob, "Majority Class Baseline")

    # 2. Logistic Regression
    print("Step 4: Training Multinomial Logistic Regression...")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train_trans, y_train)
    lr_pred = lr.predict(X_test_trans)
    lr_prob = lr.predict_proba(X_test_trans)
    eval_results["logistic_regression"] = evaluate_multiclass(y_test, lr_pred, lr_prob, "Multinomial Logistic Regression")

    # 3. XGBoost (No Credit_Score) - Production Champion
    print("Step 5: Training XGBoost Multiclass (Core 42 Features - NO Credit_Score)...")
    xgb_champion = XGBClassifier(
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
    xgb_champion.fit(
        X_train_trans, y_train,
        eval_set=[(X_val_trans, y_val)],
        verbose=False,
    )
    xgb_pred = xgb_champion.predict(X_test_trans)
    xgb_prob = xgb_champion.predict_proba(X_test_trans)
    eval_results["xgboost"] = evaluate_multiclass(y_test, xgb_pred, xgb_prob, "XGBoost Classifier")

    # 4. XGBoost With Credit_Score (Leakage Study)
    print("Step 6: Training XGBoost WITH Credit_Score (Target Leakage Study)...")
    FEATURES_WITH_CS = EXPECTED_COLUMNS + ["Credit_Score"]
    prep_cs = IndianCreditPreprocessor()
    prep_cs.numeric_features = NUMERIC_FEATURES + ["Credit_Score"]
    prep_cs.fit(clean_merged.iloc[idx_train][FEATURES_WITH_CS])
    X_train_cs = prep_cs.transform(clean_merged.iloc[idx_train][FEATURES_WITH_CS])
    X_val_cs = prep_cs.transform(clean_merged.iloc[idx_val][FEATURES_WITH_CS])
    X_test_cs = prep_cs.transform(clean_merged.iloc[idx_test][FEATURES_WITH_CS])

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
    xgb_cs.fit(X_train_cs, y_train, eval_set=[(X_val_cs, y_val)], verbose=False)
    xgb_cs_pred = xgb_cs.predict(X_test_cs)
    xgb_cs_prob = xgb_cs.predict_proba(X_test_cs)
    eval_results["xgboost_with_credit_score"] = evaluate_multiclass(y_test, xgb_cs_pred, xgb_cs_prob, "XGBoost (With Credit_Score)")

    # 5. Fit SHAP TreeExplainer
    print("Step 7: Fitting SHAP TreeExplainer...")
    explainer = shap.TreeExplainer(xgb_champion)

    # 6. Evaluate Unseen Dataset
    if unseen_path.exists():
        print("Step 8: Evaluating Unseen Dataset (100 rows)...")
        df_unseen = pd.read_excel(unseen_path)
        unseen_trans = preprocessor.transform(df_unseen)
        unseen_preds = xgb_champion.predict(unseen_trans)
        unseen_probs = xgb_champion.predict_proba(unseen_trans)

        unseen_records = []
        for i in range(len(df_unseen)):
            pred_lbl = REV_TARGET_MAP[int(unseen_preds[i])]
            pr_dict = {cls: round(float(unseen_probs[i][j]), 4) for j, cls in enumerate(TARGET_CLASSES)}
            unseen_records.append({
                "index": i,
                "predicted_category": pred_lbl,
                "class_probabilities": pr_dict
            })
        
        with open(EVAL_DIR / "unseen_predictions.json", "w", encoding="utf-8") as f:
            json.dump(unseen_records, f, indent=2)
        pd.DataFrame(unseen_records).to_csv(EVAL_DIR / "unseen_predictions.csv", index=False)
        print(f"Unseen predictions written to {EVAL_DIR / 'unseen_predictions.json'}")

    # 7. Save Production Artifacts
    print("Step 9: Persisting production model artifacts...")
    version_tag = "credit_xgboost_v1"
    model_path = ARTIFACTS_DIR / f"{version_tag}.joblib"
    prep_path = ARTIFACTS_DIR / f"{version_tag}_preprocessor.joblib"
    expl_path = ARTIFACTS_DIR / f"{version_tag}_explainer.joblib"

    joblib.dump(xgb_champion, model_path)
    joblib.dump(preprocessor, prep_path)
    joblib.dump(explainer, expl_path)

    # Save model comparison
    comp_path = EVAL_DIR / "model_comparison.json"
    with open(comp_path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    print(f"Artifacts saved: \n  Model: {model_path}\n  Preprocessor: {prep_path}\n  Explainer: {expl_path}")

    # 8. Register in database
    if auto_register:
        print("Step 10: Auto-registering champion model in database...")
        db = SessionLocal()
        try:
            now_dt = datetime.now(UTC)
            chksum = compute_file_sha256(model_path)
            db.query(ModelVersion).filter(ModelVersion.status == "active").update({"status": "archived"})
            
            existing = db.query(ModelVersion).filter(ModelVersion.version == version_tag).first()
            if existing:
                existing.metrics_json = json.dumps(eval_results["xgboost"])
                existing.status = "active"
                existing.checksum = chksum
                existing.dataset_id = "Indian_Banking_CIBIL_Merged_2026"
                existing.feature_schema_version = "v2.0_indian_credit"
                existing.trained_at = now_dt
            else:
                db_model = ModelVersion(
                    model_name="xgboost",
                    version=version_tag,
                    dataset_id="Indian_Banking_CIBIL_Merged_2026",
                    feature_schema_version="v2.0_indian_credit",
                    preprocessing_artifact=str(prep_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    model_artifact=str(model_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                    metrics_json=json.dumps(eval_results["xgboost"]),
                    status="active",
                    checksum=chksum,
                    trained_at=now_dt
                )
                db.add(db_model)

            db.commit()
            print(f"Model {version_tag} registered as active in database.")
        finally:
            db.close()

    return eval_results


if __name__ == "__main__":
    train_and_evaluate(auto_register=True)
