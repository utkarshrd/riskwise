import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from backend.app.core.config import settings
from backend.app.db.models import ModelVersion
from ml.data_validation import (
    CATEGORICAL_FEATURES,
    EXPECTED_COLUMNS,
    TARGET_CLASSES,
    validate_borrower_input,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class FeatureContribution(BaseModel):
    feature_name: str
    feature_value: float | str
    shap_value: float
    impact_direction: str  # INCREASES_RISK or REDUCES_RISK


class CreditScoreResult(BaseModel):
    model_version: str
    predicted_category: str = "P2"
    class_probabilities: dict[str, float] = Field(default_factory=dict)
    probability_of_default: float = 0.0
    relative_risk_score: float = 0.0
    relative_risk_band: str = "MODERATE_RISK"  # LOW_RISK, MODERATE_RISK, ELEVATED_RISK, HIGH_RISK
    percentile_framing: str = ""
    decision_threshold: float = 0.5
    binary_classification: str = "NON_DEFAULT_PREDICTED"
    assumptions: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    methodology_disclosure: str = (
        "Educational credit-category classifier trained on Indian banking and CIBIL bureau benchmark. "
        "Does NOT represent official Indian CIBIL score or guaranteed loan decision."
    )
    proxy_dataset_disclaimer: str = (
        "Predicted credit quality tier (P1-P4) based on Indian bureau benchmark. "
        "Not calibrated to individual lender approval policies or official credit bureau scores."
    )


class CreditExplanationResult(BaseModel):
    model_version: str
    predicted_category: str = "P2"
    class_probabilities: dict[str, float] = Field(default_factory=dict)
    probability_of_default: float = 0.0
    base_value: float = 0.0
    top_contributions: list[FeatureContribution] = Field(default_factory=list)
    all_contributions: dict[str, float] = Field(default_factory=dict)


class ActionableChangeResult(BaseModel):
    feature: str
    original_value: float | str
    modified_value: float | str
    risk_delta: float
    direction: str  # RISK_REDUCED, RISK_INCREASED, UNCHANGED
    impact_description: str


class WhatIfScenarioComparison(BaseModel):
    baseline_category: str = "P2"
    counterfactual_category: str = "P2"
    baseline_probabilities: dict[str, float] = Field(default_factory=dict)
    counterfactual_probabilities: dict[str, float] = Field(default_factory=dict)
    baseline_probability: float = 0.0
    baseline_risk_band: str = "MODERATE_RISK"
    counterfactual_probability: float = 0.0
    counterfactual_risk_band: str = "MODERATE_RISK"
    probability_delta: float = 0.0
    direction_of_change: str = "UNCHANGED"
    modified_features: dict[str, dict[str, Any]] = Field(default_factory=dict)
    actionable_mode: bool = False
    ranked_changes: list[ActionableChangeResult] = Field(default_factory=list)


# Safe Demonstration Profiles - neutral Category P1-P4 based on Approved_Flag
SAMPLE_PROFILES = [
    {
        "sample_id": "p1_sample",
        "label": "Category P1 Profile",
        "description": "Benchmark profile with P1 characteristics: higher income, established credit lines, zero delinquency.",
        "expected_category": "P1",
        "features": {
            "pct_tl_open_L6M": 0.0,
            "pct_tl_closed_L6M": 0.0,
            "Tot_TL_closed_L12M": 1,
            "pct_tl_closed_L12M": 0.1,
            "Tot_Missed_Pmnt": 0,
            "CC_TL": 2,
            "Home_TL": 1,
            "PL_TL": 0,
            "Secured_TL": 2,
            "Unsecured_TL": 1,
            "Other_TL": 0,
            "Age_Oldest_TL": 120,
            "Age_Newest_TL": 24,
            "time_since_recent_payment": 1,
            "max_recent_level_of_deliq": 0,
            "num_deliq_6_12mts": 0,
            "num_times_60p_dpd": 0,
            "num_std_12mts": 12,
            "num_sub": 0,
            "num_sub_6mts": 0,
            "num_sub_12mts": 0,
            "num_dbt": 0,
            "num_dbt_12mts": 0,
            "num_lss": 0,
            "recent_level_of_deliq": 0,
            "CC_enq_L12m": 0,
            "PL_enq_L12m": 0,
            "time_since_recent_enq": 18,
            "enq_L3m": 0,
            "NETMONTHLYINCOME": 95000,
            "Time_With_Curr_Empr": 72,
            "CC_Flag": 1,
            "PL_Flag": 0,
            "pct_PL_enq_L6m_of_ever": 0.0,
            "pct_CC_enq_L6m_of_ever": 0.0,
            "HL_Flag": 1,
            "GL_Flag": 0,
            "MARITALSTATUS": "Married",
            "EDUCATION": "POST-GRADUATE",
            "GENDER": "M",
            "last_prod_enq2": "HL",
            "first_prod_enq2": "HL"
        }
    },
    {
        "sample_id": "p2_sample",
        "label": "Category P2 Profile",
        "description": "Benchmark profile with P2 characteristics: moderate income, clean recent payment record, standard accounts.",
        "expected_category": "P2",
        "features": {
            "pct_tl_open_L6M": 0.15,
            "pct_tl_closed_L6M": 0.0,
            "Tot_TL_closed_L12M": 0,
            "pct_tl_closed_L12M": 0.0,
            "Tot_Missed_Pmnt": 0,
            "CC_TL": 1,
            "Home_TL": 0,
            "PL_TL": 1,
            "Secured_TL": 0,
            "Unsecured_TL": 2,
            "Other_TL": 1,
            "Age_Oldest_TL": 48,
            "Age_Newest_TL": 6,
            "time_since_recent_payment": 2,
            "max_recent_level_of_deliq": 0,
            "num_deliq_6_12mts": 0,
            "num_times_60p_dpd": 0,
            "num_std_12mts": 12,
            "num_sub": 0,
            "num_sub_6mts": 0,
            "num_sub_12mts": 0,
            "num_dbt": 0,
            "num_dbt_12mts": 0,
            "num_lss": 0,
            "recent_level_of_deliq": 0,
            "CC_enq_L12m": 1,
            "PL_enq_L12m": 1,
            "time_since_recent_enq": 4,
            "enq_L3m": 1,
            "NETMONTHLYINCOME": 42000,
            "Time_With_Curr_Empr": 36,
            "CC_Flag": 1,
            "PL_Flag": 1,
            "pct_PL_enq_L6m_of_ever": 0.5,
            "pct_CC_enq_L6m_of_ever": 0.5,
            "HL_Flag": 0,
            "GL_Flag": 0,
            "MARITALSTATUS": "Married",
            "EDUCATION": "GRADUATE",
            "GENDER": "M",
            "last_prod_enq2": "PL",
            "first_prod_enq2": "CC"
        }
    },
    {
        "sample_id": "p3_sample",
        "label": "Category P3 Profile",
        "description": "Benchmark profile with P3 characteristics: lower income, occasional payment delays, multiple recent inquiries.",
        "expected_category": "P3",
        "features": {
            "pct_tl_open_L6M": 0.35,
            "pct_tl_closed_L6M": 0.0,
            "Tot_TL_closed_L12M": 0,
            "pct_tl_closed_L12M": 0.0,
            "Tot_Missed_Pmnt": 2,
            "CC_TL": 2,
            "Home_TL": 0,
            "PL_TL": 2,
            "Secured_TL": 0,
            "Unsecured_TL": 4,
            "Other_TL": 0,
            "Age_Oldest_TL": 24,
            "Age_Newest_TL": 3,
            "time_since_recent_payment": 4,
            "max_recent_level_of_deliq": 1,
            "num_deliq_6_12mts": 1,
            "num_times_60p_dpd": 1,
            "num_std_12mts": 8,
            "num_sub": 1,
            "num_sub_6mts": 1,
            "num_sub_12mts": 1,
            "num_dbt": 0,
            "num_dbt_12mts": 0,
            "num_lss": 0,
            "recent_level_of_deliq": 1,
            "CC_enq_L12m": 3,
            "PL_enq_L12m": 4,
            "time_since_recent_enq": 1,
            "enq_L3m": 3,
            "NETMONTHLYINCOME": 22000,
            "Time_With_Curr_Empr": 14,
            "CC_Flag": 1,
            "PL_Flag": 1,
            "pct_PL_enq_L6m_of_ever": 0.8,
            "pct_CC_enq_L6m_of_ever": 0.7,
            "HL_Flag": 0,
            "GL_Flag": 0,
            "MARITALSTATUS": "Single",
            "EDUCATION": "12TH",
            "GENDER": "M",
            "last_prod_enq2": "PL",
            "first_prod_enq2": "PL"
        }
    },
    {
        "sample_id": "p4_sample",
        "label": "Category P4 Profile",
        "description": "Benchmark profile with P4 characteristics: multiple missed payments, elevated past delinquency signals.",
        "expected_category": "P4",
        "features": {
            "pct_tl_open_L6M": 0.5,
            "pct_tl_closed_L6M": 0.0,
            "Tot_TL_closed_L12M": 0,
            "pct_tl_closed_L12M": 0.0,
            "Tot_Missed_Pmnt": 6,
            "CC_TL": 3,
            "Home_TL": 0,
            "PL_TL": 3,
            "Secured_TL": 0,
            "Unsecured_TL": 6,
            "Other_TL": 0,
            "Age_Oldest_TL": 18,
            "Age_Newest_TL": 1,
            "time_since_recent_payment": 8,
            "max_recent_level_of_deliq": 2,
            "num_deliq_6_12mts": 3,
            "num_times_60p_dpd": 3,
            "num_std_12mts": 4,
            "num_sub": 2,
            "num_sub_6mts": 2,
            "num_sub_12mts": 2,
            "num_dbt": 1,
            "num_dbt_12mts": 1,
            "num_lss": 0,
            "recent_level_of_deliq": 2,
            "CC_enq_L12m": 5,
            "PL_enq_L12m": 6,
            "time_since_recent_enq": 0,
            "enq_L3m": 5,
            "NETMONTHLYINCOME": 14000,
            "Time_With_Curr_Empr": 6,
            "CC_Flag": 1,
            "PL_Flag": 1,
            "pct_PL_enq_L6m_of_ever": 1.0,
            "pct_CC_enq_L6m_of_ever": 1.0,
            "HL_Flag": 0,
            "GL_Flag": 0,
            "MARITALSTATUS": "Single",
            "EDUCATION": "SSC",
            "GENDER": "M",
            "last_prod_enq2": "PL",
            "first_prod_enq2": "PL"
        }
    }
]


def map_profile_to_features(
    credit_limit: float = 200000.0,
    bill_amounts: list[float] | None = None,
    payment_amounts: list[float] | None = None,
    months_late: list[int] | None = None,
    age: int | None = 35,
    net_monthly_income: float = 45000.0,
    time_with_curr_empr: int = 36,
    marital_status: str = "Married",
    education: str = "GRADUATE",
    gender: str = "M"
) -> dict[str, Any]:
    """
    Constructs a valid Indian Credit feature dictionary from standard user inputs.
    """
    months_late = months_late or [0] * 6
    bill_amounts = bill_amounts or [25000.0] * 6
    payment_amounts = payment_amounts or [2500.0] * 6

    missed_count = sum(1 for m in months_late if m > 0)
    worst_dpd = max(months_late) if months_late else 0
    dpd_60p = sum(1 for m in months_late if m >= 2)

    features = dict(SAMPLE_PROFILES[1]["features"])  # Start with standard P2 baseline
    features["NETMONTHLYINCOME"] = float(net_monthly_income)
    features["Time_With_Curr_Empr"] = int(time_with_curr_empr)
    features["MARITALSTATUS"] = marital_status
    features["EDUCATION"] = education
    features["GENDER"] = gender
    features["Tot_Missed_Pmnt"] = missed_count
    features["num_times_60p_dpd"] = dpd_60p
    features["recent_level_of_deliq"] = 1 if worst_dpd > 0 else 0
    features["max_recent_level_of_deliq"] = 1 if worst_dpd > 0 else 0
    return features


PROTECTED_ATTRIBUTES = {"SEX", "AGE", "MARRIAGE", "EDUCATION", "GENDER", "MARITALSTATUS"}
# Borrower-controllable features in both Indian Credit and benchmark legacy schemas.
# Only these may be modified in actionable what-if mode (protected attributes excluded).
CONTROLLABLE_FEATURES = {
    # Indian credit schema controllable features
    "Tot_Missed_Pmnt",
    "num_times_60p_dpd",
    "num_deliq_6_12mts",
    "enq_L3m",
    "CC_enq_L12m",
    "PL_enq_L12m",
    "time_since_recent_enq",
    "time_since_recent_payment",
    "NETMONTHLYINCOME",
    "Time_With_Curr_Empr",
    "pct_PL_enq_L6m_of_ever",
    "pct_CC_enq_L6m_of_ever",
    "pct_tl_open_L6M",
    "pct_tl_closed_L6M",
    "Tot_TL_closed_L12M",
    "num_sub",
    "num_sub_6mts",
    "num_sub_12mts",
    "last_prod_enq2",
    "first_prod_enq2",
    # Legacy UCI benchmark controllable features
    "LIMIT_BAL",
    "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
    "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
}


class CreditService:
    def __init__(self, db: Session):
        self.db = db
        self.active_model_version = self._get_active_model_record()
        self.model = None
        self.preprocessor = None
        self.explainer = None
        if self.active_model_version:
            self._load_artifacts()

    def _get_active_model_record(self) -> ModelVersion | None:
        return self.db.query(ModelVersion).filter(ModelVersion.status == "active").first()

    def _load_artifacts(self):
        rec = self.active_model_version
        if not rec:
            return
        model_p = Path(rec.model_artifact)
        prep_p = Path(rec.preprocessing_artifact)
        model_path = model_p if model_p.is_absolute() else (settings.REPO_ROOT / model_p)
        prep_path = prep_p if prep_p.is_absolute() else (settings.REPO_ROOT / prep_p)
        explainer_p = model_p.parent / f"{rec.version}_explainer.joblib"
        explainer_path = explainer_p if explainer_p.is_absolute() else (settings.REPO_ROOT / explainer_p)

        if model_path.exists():
            self.model = joblib.load(model_path)
        if prep_path.exists():
            self.preprocessor = joblib.load(prep_path)
        if explainer_path.exists():
            self.explainer = joblib.load(explainer_path)

    def _format_input(self, features: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
        # If input has legacy UCI columns but missing Indian columns, convert them
        if "LIMIT_BAL" in features and "NETMONTHLYINCOME" not in features:
            converted = map_profile_to_features(
                credit_limit=features.get("LIMIT_BAL", 200000.0),
                bill_amounts=[features.get(f"BILL_AMT{i}", 20000.0) for i in range(1, 7)],
                payment_amounts=[features.get(f"PAY_AMT{i}", 2000.0) for i in range(1, 7)],
                months_late=[int(features.get(f"PAY_{i}", 0)) for i in [0, 2, 3, 4, 5, 6]],
                age=int(features.get("AGE", 35))
            )
            features = converted

        cleaned_dict, warnings = validate_borrower_input(features)
        df_input = pd.DataFrame([cleaned_dict])
        return df_input, warnings

    def score(self, features: dict[str, Any]) -> CreditScoreResult:
        if not self.model or not self.preprocessor:
            raise RuntimeError("No active credit model artifact is loaded.")

        metrics = {}
        if self.active_model_version and self.active_model_version.metrics_json:
            try:
                metrics = json.loads(self.active_model_version.metrics_json)
            except (json.JSONDecodeError, TypeError):
                metrics = {}

        if not metrics or "decision_threshold" not in metrics or "risk_band_cutoffs" not in metrics:
            raise RuntimeError("model metadata incomplete")

        df_input, warnings = self._format_input(features)
        X_trans = self.preprocessor.transform(df_input)
        probs = self.model.predict_proba(X_trans)[0]

        prob_dict = {
            "P1": round(float(probs[0]), 4),
            "P2": round(float(probs[1]), 4),
            "P3": round(float(probs[2]), 4),
            "P4": round(float(probs[3]), 4),
        }

        pred_idx = int(np.argmax(probs))
        predicted_cat = TARGET_CLASSES[pred_idx]

        # Estimated high-risk tier (P3+P4) probability
        prob_high_risk = round(float(probs[2] + probs[3]), 4)
        relative_risk_score = round(float(probs[2] * 0.5 + probs[3] * 1.0), 4)

        if predicted_cat == "P1":
            band = "LOW_RISK"
            framing = "Category P1: Model predicted class P1 (Approved_Flag benchmark category)."
        elif predicted_cat == "P2":
            band = "MODERATE_RISK"
            framing = "Category P2: Model predicted class P2 (Approved_Flag benchmark category)."
        elif predicted_cat == "P3":
            band = "ELEVATED_RISK"
            framing = "Category P3: Model predicted class P3 (Approved_Flag benchmark category)."
        else:
            band = "HIGH_RISK"
            framing = "Category P4: Model predicted class P4 (Approved_Flag benchmark category)."

        binary_cls = "DEFAULT_PREDICTED" if predicted_cat in ["P3", "P4"] else "NON_DEFAULT_PREDICTED"

        assumptions = {
            "benchmark_dataset": "Indian Banking & CIBIL Bureau Dataset (51,336 records)",
            "predicted_category": predicted_cat,
            "classes": TARGET_CLASSES,
            "decision_threshold": 0.5,
            "class_distribution_in_training": {"P2": "62.7%", "P3": "14.5%", "P4": "11.5%", "P1": "11.3%"}
        }

        return CreditScoreResult(
            model_version=self.active_model_version.version,
            predicted_category=predicted_cat,
            class_probabilities=prob_dict,
            probability_of_default=prob_high_risk,
            relative_risk_score=relative_risk_score,
            relative_risk_band=band,
            percentile_framing=framing,
            decision_threshold=0.5,
            binary_classification=binary_cls,
            assumptions=assumptions,
            warnings=warnings
        )

    def explain(self, features: dict[str, Any], top_n: int = 8) -> CreditExplanationResult:
        if not self.model or not self.preprocessor or not self.explainer:
            raise RuntimeError("Credit explainer artifact is not loaded.")

        df_input, _ = self._format_input(features)
        X_trans = self.preprocessor.transform(df_input)
        probs = self.model.predict_proba(X_trans)[0]
        pred_idx = int(np.argmax(probs))
        predicted_cat = TARGET_CLASSES[pred_idx]

        prob_dict = {
            "P1": round(float(probs[0]), 4),
            "P2": round(float(probs[1]), 4),
            "P3": round(float(probs[2]), 4),
            "P4": round(float(probs[3]), 4),
        }

        # Calculate SHAP values
        shap_vals = self.explainer.shap_values(X_trans)
        # TreeExplainer for multi:softprob returns shape (N, num_features, num_classes) or list of arrays
        if isinstance(shap_vals, list):
            # List of 4 arrays, one per class
            sv = shap_vals[pred_idx][0]
        elif len(np.shape(shap_vals)) == 3:
            # (1, num_features, 4)
            sv = shap_vals[0, :, pred_idx]
        else:
            sv = shap_vals[0]

        feat_names = getattr(self.preprocessor, "get_feature_names_out", lambda: EXPECTED_COLUMNS)()

        contributions = {}
        contrib_list = []

        # Human-readable labels for primary features
        for idx, feat_name in enumerate(feat_names):
            base_col = feat_name.split("__")[-1] if "__" in feat_name else feat_name
            raw_val = None
            if base_col in df_input.columns:
                raw_val = df_input[base_col].iloc[0]
            else:
                for cat in CATEGORICAL_FEATURES:
                    if feat_name.startswith(f"{cat}_") or base_col.startswith(f"{cat}_"):
                        cat_val = df_input[cat].iloc[0] if cat in df_input.columns else ""
                        raw_val = str(cat_val)
                        break
            if raw_val is None:
                raw_val = 0.0

            s_val = float(sv[idx]) if idx < len(sv) else 0.0

            contributions[feat_name] = round(s_val, 4)

            # Impact direction: for P1/P2, positive SHAP value supports favorable tier
            # For P3/P4, positive SHAP value drives elevated tier
            if predicted_cat in ["P1", "P2"]:
                impact_dir = "REDUCES_RISK" if s_val > 0 else "INCREASES_RISK"
            else:
                impact_dir = "INCREASES_RISK" if s_val > 0 else "REDUCES_RISK"

            contrib_list.append(FeatureContribution(
                feature_name=feat_name,
                feature_value=raw_val if isinstance(raw_val, (int, float, str)) else str(raw_val),
                shap_value=round(s_val, 4),
                impact_direction=impact_dir
            ))

        # Sort by absolute SHAP value
        contrib_list.sort(key=lambda c: abs(c.shap_value), reverse=True)

        base_val = 0.0
        if hasattr(self.explainer, "expected_value"):
            exp_val = self.explainer.expected_value
            if isinstance(exp_val, (list, np.ndarray)):
                base_val = float(exp_val[pred_idx]) if pred_idx < len(exp_val) else float(exp_val[0])
            else:
                base_val = float(exp_val)

        return CreditExplanationResult(
            model_version=self.active_model_version.version,
            predicted_category=predicted_cat,
            class_probabilities=prob_dict,
            probability_of_default=round(float(probs[2] + probs[3]), 4),
            base_value=round(base_val, 4),
            top_contributions=contrib_list[:top_n],
            all_contributions=contributions
        )

    def what_if(
        self,
        baseline_features: dict[str, Any],
        modifications: dict[str, Any],
        actionable_only: bool = False
    ) -> WhatIfScenarioComparison:
        if actionable_only:
            for k in modifications:
                if k in PROTECTED_ATTRIBUTES:
                    raise ValueError(f"Modifying protected attribute '{k}' is prohibited in actionable what-if mode.")
                if k not in CONTROLLABLE_FEATURES:
                    raise ValueError(f"Feature '{k}' is not an actionable, borrower-controllable feature.")

        base_res = self.score(baseline_features)

        mod_features = dict(baseline_features)
        feature_diffs = {}
        for k, v in modifications.items():
            orig_v = baseline_features.get(k, None)
            mod_features[k] = v
            feature_diffs[k] = {"original": orig_v, "modified": v}

        mod_res = self.score(mod_features)
        delta = round(mod_res.probability_of_default - base_res.probability_of_default, 4)

        if mod_res.predicted_category < base_res.predicted_category:  # e.g. P1 < P2
            direction = "CATEGORY_UPGRADED"
        elif mod_res.predicted_category > base_res.predicted_category:  # e.g. P3 > P2
            direction = "CATEGORY_DOWNGRADED"
        elif delta < -0.01:
            direction = "RISK_REDUCED"
        elif delta > 0.01:
            direction = "RISK_INCREASED"
        else:
            direction = "UNCHANGED"

        ranked_changes: list[ActionableChangeResult] = []
        for k, v in modifications.items():
            single_mod = dict(baseline_features)
            orig_v = baseline_features.get(k, None)
            single_mod[k] = v
            single_res = self.score(single_mod)
            s_delta = round(single_res.probability_of_default - base_res.probability_of_default, 4)

            if single_res.predicted_category < base_res.predicted_category or s_delta < -0.005:
                s_dir = "RISK_REDUCED"
                desc = f"Improves profile towards {single_res.predicted_category}"
            elif single_res.predicted_category > base_res.predicted_category or s_delta > 0.005:
                s_dir = "RISK_INCREASED"
                desc = f"Shifts profile towards {single_res.predicted_category}"
            else:
                s_dir = "UNCHANGED"
                desc = "No material shift in category"

            ranked_changes.append(ActionableChangeResult(
                feature=k,
                original_value=orig_v,
                modified_value=v,
                risk_delta=s_delta,
                direction=s_dir,
                impact_description=desc
            ))

        ranked_changes.sort(key=lambda c: c.risk_delta)

        return WhatIfScenarioComparison(
            baseline_category=base_res.predicted_category,
            counterfactual_category=mod_res.predicted_category,
            baseline_probabilities=base_res.class_probabilities,
            counterfactual_probabilities=mod_res.class_probabilities,
            baseline_probability=base_res.probability_of_default,
            baseline_risk_band=base_res.relative_risk_band,
            counterfactual_probability=mod_res.probability_of_default,
            counterfactual_risk_band=mod_res.relative_risk_band,
            probability_delta=delta,
            direction_of_change=direction,
            modified_features=feature_diffs,
            actionable_mode=actionable_only,
            ranked_changes=ranked_changes
        )
