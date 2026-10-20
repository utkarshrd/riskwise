
import numpy as np
import pandas as pd
import pytest
from backend.app.core.config import settings
from ml.data_validation import EXPECTED_COLUMNS, NUMERIC_FEATURES, TARGET_COL
from ml.preprocessing import CreditPreprocessor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import train_test_split


def test_seeded_retraining_reproducibility():
    """
    PRD §4.1 FR-CR-03 & Phase 1 requirement:
    Verify that retraining candidate models on a fixed seeded sample reproduces
    the exact same metrics, proving zero non-deterministic leakage or randomness drift.
    """
    data_file = settings.DATA_DIR / "processed" / "credit_indian_cleaned.csv"
    if not data_file.exists():
        data_file = settings.DATA_DIR / "processed" / "credit_default_cleaned.csv"
    if not data_file.exists():
        pytest.skip("Processed dataset not available for retraining test.")

    df = pd.read_csv(data_file)
    sample_df = df.sample(n=1000, random_state=42).copy()

    X = sample_df[EXPECTED_COLUMNS]
    target_raw = sample_df[TARGET_COL].values
    # Map to binary (P3/P4 vs P1/P2) or integer for logistic regression test
    target_map = {"P1": 0, "P2": 0, "P3": 1, "P4": 1}
    y = np.array([target_map.get(str(t), 0) for t in target_raw])

    # Run 1
    X_train1, X_test1, y_train1, y_test1 = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    prep1 = CreditPreprocessor(feature_names=EXPECTED_COLUMNS)
    X_train1_scaled = prep1.fit_transform(X_train1)
    X_test1_scaled = prep1.transform(X_test1)

    model1 = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
    model1.fit(X_train1_scaled, y_train1)
    probs1 = model1.predict_proba(X_test1_scaled)[:, 1]
    auc1 = roc_auc_score(y_test1, probs1)
    f1_1 = f1_score(y_test1, (probs1 >= 0.5).astype(int), zero_division=0)

    # Run 2 (Independent re-execution with identical seed)
    X_train2, X_test2, y_train2, y_test2 = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    prep2 = CreditPreprocessor(feature_names=EXPECTED_COLUMNS)
    X_train2_scaled = prep2.fit_transform(X_train2)
    X_test2_scaled = prep2.transform(X_test2)

    model2 = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
    model2.fit(X_train2_scaled, y_train2)
    probs2 = model2.predict_proba(X_test2_scaled)[:, 1]
    auc2 = roc_auc_score(y_test2, probs2)
    f1_2 = f1_score(y_test2, (probs2 >= 0.5).astype(int), zero_division=0)

    # Assert exact bit-level / 8-decimal reproducibility
    assert np.allclose(X_train1_scaled, X_train2_scaled, atol=1e-10)
    assert np.allclose(X_test1_scaled, X_test2_scaled, atol=1e-10)
    assert np.allclose(probs1, probs2, atol=1e-10)
    assert abs(auc1 - auc2) < 1e-10
    assert abs(f1_1 - f1_2) < 1e-10


def test_no_test_set_resampling_leakage():
    """
    PRD §4.1 FR-CR-03 & §14:
    Verify that preprocessing fit occurs exclusively on training data and
    that test set distributions do not leak into scaling statistics.
    """
    train_data = pd.DataFrame({
        col: [10.0, 20.0, 30.0] if col in NUMERIC_FEATURES else ["Married", "Single", "Married"]
        for col in EXPECTED_COLUMNS
    })
    test_data = pd.DataFrame({
        col: [100.0, 200.0, 300.0] if col in NUMERIC_FEATURES else ["Single", "Single", "Married"]
        for col in EXPECTED_COLUMNS
    })

    prep = CreditPreprocessor(feature_names=EXPECTED_COLUMNS)
    prep.fit(train_data)

    # The mean should reflect train_data (20.0), NOT test_data
    assert abs(prep.scaler.mean_[0] - 20.0) < 1e-6
    scaled_test = prep.transform(test_data)
    assert scaled_test.shape[0] == 3
