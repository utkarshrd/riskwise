from typing import Any

from pydantic import BaseModel, Field


class EMIRequest(BaseModel):
    principal: float = Field(..., gt=0, description="Loan principal amount in currency units")
    annual_interest_rate: float = Field(..., ge=0, description="Annual interest rate as decimal (e.g. 0.105 for 10.5%)")
    tenure_months: int = Field(..., gt=0, description="Loan tenure in months")
    include_schedule: bool = Field(default=False, description="Whether to include monthly amortization breakdown")


class EMIResponse(BaseModel):
    principal: float
    annual_interest_rate: float
    tenure_months: int
    monthly_emi: float
    total_interest: float
    total_payment: float
    amortization_schedule: list[dict[str, Any]] = Field(default_factory=list)


class StressTestScenarioSchema(BaseModel):
    income_reduction_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage reduction in monthly income")
    essential_expense_surge_pct: float = Field(default=0.0, ge=0.0, description="Percentage increase in essential expenses")
    discretionary_expense_surge_pct: float = Field(default=0.0, ge=0.0, description="Percentage increase in discretionary expenses")
    interest_rate_hike_pct: float = Field(default=0.0, ge=0.0, description="Percentage point increase in interest rates")
    existing_emi_floating_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of existing EMIs on floating rate subject to rate hike (0.0 = fixed, 1.0 = fully floating)")
    emergency_fund_target_months: float = Field(default=6.0, gt=0.0, description="Planning assumption target runway months for emergency fund")


class StressTestRequest(BaseModel):
    monthly_income: float = Field(..., ge=0, description="Current monthly net income")
    essential_expenses: float = Field(..., ge=0, description="Baseline essential living expenses")
    discretionary_expenses: float = Field(default=0.0, ge=0, description="Baseline discretionary spending")
    existing_emis: float = Field(default=0.0, ge=0, description="Existing ongoing monthly loan obligations")
    liquid_savings: float = Field(default=0.0, ge=0, description="Readily accessible emergency liquid reserves")
    proposed_loan_principal: float = Field(default=0.0, ge=0, description="Optional new loan principal to evaluate")
    proposed_loan_interest_rate: float = Field(default=0.0, ge=0.0, description="Optional new loan annual interest rate")
    proposed_loan_tenure_months: int = Field(default=0, ge=0, description="Optional new loan tenure in months")
    scenario: StressTestScenarioSchema = Field(default_factory=StressTestScenarioSchema)


class StressTestResponse(BaseModel):
    baseline_income: float
    baseline_essential_expenses: float
    baseline_discretionary_expenses: float
    baseline_existing_emis: float
    proposed_emi: float
    liquid_savings: float

    baseline_surplus: float
    baseline_emi_to_income_ratio: float | None
    baseline_runway_months: float | None
    baseline_emergency_fund_gap: float

    stressed_income: float
    stressed_essential_expenses: float
    stressed_discretionary_expenses: float
    stressed_existing_emis: float
    stressed_proposed_emi: float

    stressed_surplus: float
    stressed_emi_to_income_ratio: float | None
    stressed_runway_months: float | None
    stressed_emergency_fund_gap: float

    surplus_change: float
    runway_change_months: float | None
    is_insolvent: bool
    risk_assessment: str
    assumptions: dict[str, Any]
