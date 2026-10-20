from typing import Any

from pydantic import BaseModel, Field


class CreditModelMetadata(BaseModel):
    id: str
    model_name: str
    version: str
    dataset_id: str
    status: str
    trained_at: str
    checksum: str
    metrics: dict[str, Any]


class CreditScoreRequest(BaseModel):
    features: dict[str, Any] = Field(
        ...,
        description="Dictionary of borrower features matching the Indian Credit schema (42 features)"
    )


class CreditScoreResponse(BaseModel):
    model_version: str
    predicted_category: str = Field(default="P2", description="Predicted credit category: P1, P2, P3, P4")
    class_probabilities: dict[str, float] = Field(default_factory=dict, description="Class probabilities for P1, P2, P3, P4")
    probability_of_default: float = Field(default=0.0, description="Relative risk index (P3+P4 combined output). Not calibrated probability of default.")
    relative_risk_score: float = Field(default=0.0, description="Relative risk index (0.0=lowest risk, 1.0=highest risk)")
    relative_risk_band: str = Field(default="MODERATE_RISK", description="LOW_RISK, MODERATE_RISK, ELEVATED_RISK, or HIGH_RISK")
    percentile_framing: str = Field(default="", description="Educational tier context")
    decision_threshold: float = Field(default=0.5, description="Decision threshold on class boundaries")
    binary_classification: str = Field(default="NON_DEFAULT_PREDICTED", description="Binary risk grouping")
    assumptions: dict[str, Any] = Field(default_factory=dict, description="Scoring assumptions and benchmark configuration")
    warnings: list[str] = Field(default_factory=list, description="Data validation warnings or anomalies")
    methodology_disclosure: str = (
        "Educational credit-category classifier trained on Indian banking and CIBIL bureau benchmark. "
        "Outputs represent relative borrower tiers (P1-P4) within historical portfolio data. "
        "Does NOT estimate official CIBIL score or guarantee lending outcomes."
    )
    proxy_dataset_disclaimer: str = (
        "Predicted credit quality category (P1-P4) based on Indian bureau benchmark. "
        "Not calibrated to individual lender approval policies or official credit bureau scores."
    )


class CreditExplainRequest(BaseModel):
    features: dict[str, Any]
    top_n: int = Field(default=8, ge=1, le=25)


class FeatureContributionSchema(BaseModel):
    feature_name: str
    feature_value: float | str
    shap_value: float
    impact_direction: str  # INCREASES_RISK or REDUCES_RISK


class CreditExplainResponse(BaseModel):
    model_version: str
    predicted_category: str = "P2"
    class_probabilities: dict[str, float] = Field(default_factory=dict)
    probability_of_default: float = 0.0
    base_value: float = 0.0
    top_contributions: list[FeatureContributionSchema] = Field(default_factory=list)
    all_contributions: dict[str, float] = Field(default_factory=dict)


class CreditProfileScoreRequest(BaseModel):
    credit_limit: float = Field(default=200000.0, gt=0, description="Borrower credit limit / exposure")
    bill_amounts: list[float] = Field(default_factory=lambda: [25000.0]*6, min_length=6, max_length=6)
    payment_amounts: list[float] = Field(default_factory=lambda: [2500.0]*6, min_length=6, max_length=6)
    months_late: list[int] = Field(default_factory=lambda: [0]*6, min_length=6, max_length=6)
    age: int | None = Field(default=35, description="Optional borrower age")
    net_monthly_income: float = Field(default=45000.0, gt=0, description="Borrower net monthly income in INR")
    time_with_curr_empr: int = Field(default=36, ge=0, description="Tenure with current employer in months")
    marital_status: str = Field(default="Married", description="Marital status (Married, Single)")
    education: str = Field(default="GRADUATE", description="Educational level")
    gender: str = Field(default="M", description="Gender (M, F)")


class ActionableChange(BaseModel):
    feature: str
    original_value: float | str
    modified_value: float | str
    risk_delta: float
    direction: str  # RISK_REDUCED, RISK_INCREASED, UNCHANGED
    impact_description: str


class WhatIfRequest(BaseModel):
    baseline_features: dict[str, Any]
    modifications: dict[str, Any] = Field(..., description="Key-value pairs of modified borrower features")
    actionable_only: bool = Field(default=False, description="Restrict modifications to borrower-controllable features")


class WhatIfResponse(BaseModel):
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
    ranked_changes: list[ActionableChange] = Field(default_factory=list)


class BorrowerProfileSample(BaseModel):
    sample_id: str
    label: str
    description: str
    features: dict[str, Any]
