"""
ml/data_validation.py

Data validation, schema enforcement, and sanity checking for the Indian Credit Dataset
(External CIBIL bureau + Internal Bank data).
"""

from typing import Any
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

# 42 Core Features matching Unseen Dataset & Merged Bank-CIBIL Schema
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

EXPECTED_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
INDIAN_CREDIT_FEATURES = EXPECTED_COLUMNS
TARGET_COL = 'Approved_Flag'
TARGET_CLASSES = ['P1', 'P2', 'P3', 'P4']

# Allowed categorical values from data inspection
ALLOWED_CATEGORIES = {
    'MARITALSTATUS': {'Married', 'Single'},
    'EDUCATION': {'12TH', 'GRADUATE', 'SSC', 'POST-GRADUATE', 'UNDER GRADUATE', 'OTHERS', 'PROFESSIONAL'},
    'GENDER': {'M', 'F'},
    'last_prod_enq2': {'PL', 'ConsumerLoan', 'others', 'AL', 'CC', 'HL'},
    'first_prod_enq2': {'PL', 'ConsumerLoan', 'others', 'AL', 'HL', 'CC'},
}

# Legacy UCI schema for reference/deprecation
LEGACY_UCI_COLUMNS = [
    'LIMIT_BAL', 'SEX', 'EDUCATION', 'MARRIAGE', 'AGE',
    'PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6',
    'BILL_AMT1', 'BILL_AMT2', 'BILL_AMT3', 'BILL_AMT4', 'BILL_AMT5', 'BILL_AMT6',
    'PAY_AMT1', 'PAY_AMT2', 'PAY_AMT3', 'PAY_AMT4', 'PAY_AMT5', 'PAY_AMT6'
]


class ValidationReport(BaseModel):
    is_valid: bool
    total_records: int
    missing_values_count: int
    sentinel_values_count: int
    features_present: list[str]
    missing_features: list[str]
    target_distribution: dict[str, int]
    summary: str


def validate_credit_data(df: pd.DataFrame) -> tuple[bool, ValidationReport, pd.DataFrame]:
    """
    Validates and cleans the merged Indian banking and CIBIL dataset.
    Converts sentinel -99999 to np.nan for numerical consistency.
    """
    df_clean = df.copy()

    # Normalize target column name
    if 'Approved_Flag' not in df_clean.columns and TARGET_COL in df_clean.columns:
        df_clean = df_clean.rename(columns={TARGET_COL: 'Approved_Flag'})

    missing_cols = [col for col in EXPECTED_COLUMNS if col not in df_clean.columns]
    total_recs = len(df_clean)

    # Count sentinels (-99999)
    sentinel_cnt = 0
    for col in NUMERIC_FEATURES:
        if col in df_clean.columns:
            s_mask = (df_clean[col] == -99999)
            sentinel_cnt += int(s_mask.sum())
            df_clean[col] = df_clean[col].replace(-99999, np.nan)

    missing_vals = int(df_clean[EXPECTED_COLUMNS].isnull().sum().sum()) if not missing_cols else 0

    target_dist = {}
    has_target = TARGET_COL in df_clean.columns
    if has_target:
        target_dist = df_clean[TARGET_COL].value_counts().to_dict()

    is_valid = (len(missing_cols) == 0) and has_target and (total_recs >= 1000)

    report = ValidationReport(
        is_valid=is_valid,
        total_records=total_recs,
        missing_values_count=missing_vals,
        sentinel_values_count=sentinel_cnt,
        features_present=[c for c in EXPECTED_COLUMNS if c in df_clean.columns],
        missing_features=missing_cols,
        target_distribution=target_dist,
        summary="Indian credit data validation passed successfully." if is_valid else f"Validation failed: missing columns {missing_cols}"
    )

    return is_valid, report, df_clean


def validate_borrower_input(features: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """
    Validates and formats a single borrower profile input for inference.
    Fills standard defaults for missing non-essential columns, checks ranges,
    and returns warnings for out-of-distribution values.
    """
    formatted = {}
    warnings = []

    for col in NUMERIC_FEATURES:
        val = features.get(col, None)
        if val is None or val == "" or val == -99999:
            # Sentinel or missing value
            formatted[col] = np.nan
        else:
            try:
                formatted[col] = float(val)
            except (ValueError, TypeError):
                formatted[col] = np.nan
                warnings.append(f"Invalid numeric value for {col}; defaulting to median imputation.")

    for col in CATEGORICAL_FEATURES:
        val = features.get(col, "Unknown")
        val_str = str(val).strip()
        allowed = ALLOWED_CATEGORIES.get(col, set())
        if allowed and val_str not in allowed:
            # Check case-insensitive match
            match = next((a for a in allowed if a.lower() == val_str.lower()), None)
            if match:
                formatted[col] = match
            else:
                formatted[col] = "others" if "others" in allowed else "Unknown"
                warnings.append(f"Unrecognized category '{val_str}' for {col}; mapped to safe default.")
        else:
            formatted[col] = val_str

    # Sanity validations
    income = formatted.get("NETMONTHLYINCOME", np.nan)
    if not np.isnan(income):
        if income <= 0:
            warnings.append("Stated net monthly income is non-positive.")
        elif income < 5000:
            warnings.append("Low monthly income relative to standard formal loan criteria.")

    missed = formatted.get("Tot_Missed_Pmnt", 0.0)
    if not np.isnan(missed) and missed >= 5:
        warnings.append(f"High number of past missed payments ({int(missed)}).")

    dpd60 = formatted.get("num_times_60p_dpd", 0.0)
    if not np.isnan(dpd60) and dpd60 >= 2:
        warnings.append("Multiple severe delinquency instances (60+ DPD) detected.")

    return formatted, warnings
