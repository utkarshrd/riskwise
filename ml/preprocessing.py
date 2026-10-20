"""
ml/preprocessing.py

Preprocessing pipeline for the Indian Credit Risk Platform.
Handles numeric median imputation, standard scaling, and one-hot encoding of categorical variables.
Safely converts sentinel -99999 values to np.nan prior to imputation.
"""

from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.data_validation import (
    CATEGORICAL_FEATURES,
    EXPECTED_COLUMNS,
    NUMERIC_FEATURES,
)

PROTECTED_ATTRIBUTES = ["SEX", "EDUCATION", "MARRIAGE", "AGE"]

ENGINEERED_COLUMNS_NO_PROTECTED = [
    "util_1", "util_2", "util_3", "util_4", "util_5", "util_6",
    "pay_ratio_1", "pay_ratio_2", "pay_ratio_3", "pay_ratio_4", "pay_ratio_5", "pay_ratio_6",
    "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "months_late_count", "worst_delay", "util_trend"
]


def engineer_features(df: pd.DataFrame, include_protected: bool = False) -> pd.DataFrame:
    """Computes currency-free engineered features for fair lending and ratio testing."""
    limit = np.maximum(df["LIMIT_BAL"].astype(float).values, 1.0)
    data = {}
    for i in range(1, 7):
        bill = df[f"BILL_AMT{i}"].astype(float).values
        data[f"util_{i}"] = bill / limit
    for i in range(1, 7):
        bill = df[f"BILL_AMT{i}"].astype(float).values
        pay = df[f"PAY_AMT{i}"].astype(float).values
        data[f"pay_ratio_{i}"] = np.where(bill <= 0, 1.0, np.clip(pay / np.maximum(bill, 1.0), 0.0, 5.0))
    delays = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
    for d in delays:
        data[d] = df[d].astype(float).values
    delay_matrix = np.column_stack([df[d].astype(float).values for d in delays])
    data["months_late_count"] = np.sum(delay_matrix > 0, axis=1).astype(float)
    data["worst_delay"] = np.maximum(0, np.max(delay_matrix, axis=1)).astype(float)
    data["util_trend"] = data["util_1"] - data["util_6"]

    req_cols = ENGINEERED_COLUMNS_NO_PROTECTED
    out_df = pd.DataFrame(data, index=df.index)
    return out_df[req_cols]


class IndianCreditPreprocessor(BaseEstimator, TransformerMixin):
    """
    Transforms Indian banking and CIBIL features:
    1. Replaces sentinel -99999 with np.nan.
    2. Imputes numeric columns with median.
    3. Scales numeric columns with StandardScaler.
    4. Encodes categorical variables (MARITALSTATUS, EDUCATION, GENDER, last_prod_enq2, first_prod_enq2)
       with OneHotEncoder(handle_unknown='ignore').
    """
    RAW_COLUMNS: ClassVar[list[str]] = EXPECTED_COLUMNS
    NUMERIC_COLS: ClassVar[list[str]] = NUMERIC_FEATURES
    CATEGORICAL_COLS: ClassVar[list[str]] = CATEGORICAL_FEATURES

    def __init__(self, feature_names: list[str] | None = None, include_protected: bool = False):
        self.feature_names = feature_names
        self.include_protected = include_protected
        self.numeric_features = [c for c in NUMERIC_FEATURES if feature_names is None or c in feature_names]
        self.categorical_features = [c for c in CATEGORICAL_FEATURES if feature_names is None or c in feature_names]
        self.column_transformer = None
        self.feature_names_out_ = None

    def fit(self, X: pd.DataFrame | np.ndarray, y: Any = None):
        cols = [c for c in (self.numeric_features + self.categorical_features) if c in X.columns]
        X_clean = X[cols].copy()
        # Clean sentinels
        for col in self.numeric_features:
            if col in X_clean.columns:
                X_clean[col] = pd.to_numeric(X_clean[col], errors="coerce").replace(-99999, np.nan)
        for col in self.categorical_features:
            if col in X_clean.columns:
                X_clean[col] = X_clean[col].astype(str).fillna("Unknown")

        num_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        cat_pipe = Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])

        self.column_transformer = ColumnTransformer([
            ("num", num_pipe, self.numeric_features),
            ("cat", cat_pipe, self.categorical_features),
        ])

        self.column_transformer.fit(X_clean)

        # Compute output feature names
        cat_names = self.column_transformer.named_transformers_["cat"].named_steps["encoder"].get_feature_names_out(self.categorical_features).tolist()
        self.feature_names_out_ = self.numeric_features + cat_names
        return self

    def transform(self, X: pd.DataFrame | dict | np.ndarray) -> np.ndarray:
        if isinstance(X, dict):
            X = pd.DataFrame([X])
        elif not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X, columns=self.RAW_COLUMNS)

        X_clean = X.copy()
        all_cols = self.numeric_features + self.categorical_features
        # Ensure all required columns exist
        for col in all_cols:
            if col not in X_clean.columns:
                X_clean[col] = np.nan if col in self.numeric_features else "Unknown"

        for col in self.numeric_features:
            X_clean[col] = pd.to_numeric(X_clean[col], errors="coerce").replace(-99999, np.nan)
        for col in self.categorical_features:
            X_clean[col] = X_clean[col].astype(str).fillna("Unknown")

        return self.column_transformer.transform(X_clean[all_cols])

    @property
    def scaler(self):
        if self.column_transformer and "num" in self.column_transformer.named_transformers_:
            return self.column_transformer.named_transformers_["num"].named_steps["scaler"]
        return None

    @property
    def imputer(self):
        if self.column_transformer and "num" in self.column_transformer.named_transformers_:
            return self.column_transformer.named_transformers_["num"].named_steps["imputer"]
        return None

    def get_feature_names_out(self, input_features=None) -> list[str]:
        return self.feature_names_out_ or self.RAW_COLUMNS


# Backward-compatible alias
CreditPreprocessor = IndianCreditPreprocessor
