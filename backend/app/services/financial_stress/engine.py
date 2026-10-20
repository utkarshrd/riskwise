from typing import Any

from pydantic import BaseModel, Field


class EMICalculationResult(BaseModel):
    principal: float
    annual_interest_rate: float
    tenure_months: int
    monthly_emi: float
    total_interest: float
    total_payment: float
    amortization_schedule: list[dict[str, Any]] = Field(default_factory=list)


class StressTestScenario(BaseModel):
    income_reduction_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Reduction in monthly income %")
    essential_expense_surge_pct: float = Field(default=0.0, ge=0.0, description="Increase in essential expenses %")
    discretionary_expense_surge_pct: float = Field(default=0.0, ge=0.0, description="Increase in discretionary expenses %")
    interest_rate_hike_pct: float = Field(default=0.0, ge=0.0, description="Percentage point increase in loan interest rates")
    existing_emi_floating_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of existing EMIs on floating rate subject to rate hike (0.0 = fixed, 1.0 = fully floating)")
    emergency_fund_target_months: float = Field(default=6.0, gt=0.0, description="Planning assumption target runway months for emergency fund")


class StressTestResult(BaseModel):
    baseline_income: float
    baseline_essential_expenses: float
    baseline_discretionary_expenses: float
    baseline_existing_emis: float
    proposed_emi: float
    liquid_savings: float

    # Baseline computed metrics
    baseline_surplus: float
    baseline_emi_to_income_ratio: float | None
    baseline_runway_months: float | None
    baseline_emergency_fund_gap: float

    # Stressed inputs
    stressed_income: float
    stressed_essential_expenses: float
    stressed_discretionary_expenses: float
    stressed_existing_emis: float
    stressed_proposed_emi: float

    # Stressed computed metrics
    stressed_surplus: float
    stressed_emi_to_income_ratio: float | None
    stressed_runway_months: float | None
    stressed_emergency_fund_gap: float

    # Summary analysis
    surplus_change: float
    runway_change_months: float | None
    is_insolvent: bool
    risk_assessment: str
    assumptions: dict[str, Any]


class FinancialStressEngine:
    @staticmethod
    def calculate_emi(
        principal: float,
        annual_interest_rate: float,
        tenure_months: int,
        include_schedule: bool = False
    ) -> EMICalculationResult:
        if principal <= 0:
            raise ValueError("Principal must be greater than zero.")
        if tenure_months <= 0:
            raise ValueError("Tenure months must be greater than zero.")
        if annual_interest_rate < 0:
            raise ValueError("Interest rate cannot be negative.")

        monthly_rate = annual_interest_rate / 12.0

        if monthly_rate == 0:
            emi = principal / tenure_months
        else:
            factor = (1.0 + monthly_rate) ** tenure_months
            emi = principal * monthly_rate * factor / (factor - 1.0)

        total_payment = emi * tenure_months
        total_interest = total_payment - principal

        schedule = []
        if include_schedule:
            remaining_balance = principal
            for month in range(1, tenure_months + 1):
                interest_payment = remaining_balance * monthly_rate if monthly_rate > 0 else 0.0
                principal_payment = emi - interest_payment
                remaining_balance = max(0.0, remaining_balance - principal_payment)
                schedule.append({
                    "month": month,
                    "payment": round(emi, 2),
                    "principal_payment": round(principal_payment, 2),
                    "interest_payment": round(interest_payment, 2),
                    "remaining_balance": round(remaining_balance, 2)
                })

        return EMICalculationResult(
            principal=round(principal, 2),
            annual_interest_rate=annual_interest_rate,
            tenure_months=tenure_months,
            monthly_emi=round(emi, 2),
            total_interest=round(total_interest, 2),
            total_payment=round(total_payment, 2),
            amortization_schedule=schedule
        )

    @classmethod
    def run_stress_test(
        cls,
        monthly_income: float,
        essential_expenses: float,
        discretionary_expenses: float,
        existing_emis: float,
        liquid_savings: float,
        proposed_loan_principal: float = 0.0,
        proposed_loan_interest_rate: float = 0.0,
        proposed_loan_tenure_months: int = 0,
        scenario: StressTestScenario | None = None
    ) -> StressTestResult:
        if monthly_income < 0:
            raise ValueError("Monthly income cannot be negative.")
        if essential_expenses < 0 or discretionary_expenses < 0 or existing_emis < 0 or liquid_savings < 0:
            raise ValueError("Expenses, EMIs, and savings cannot be negative.")

        if scenario is None:
            scenario = StressTestScenario()

        # Calculate proposed EMI if loan parameters provided
        proposed_emi = 0.0
        if proposed_loan_principal > 0 and proposed_loan_tenure_months > 0:
            emi_res = cls.calculate_emi(
                proposed_loan_principal,
                proposed_loan_interest_rate,
                proposed_loan_tenure_months
            )
            proposed_emi = emi_res.monthly_emi

        # Baseline calculations
        total_emis_baseline = existing_emis + proposed_emi
        baseline_surplus = monthly_income - essential_expenses - discretionary_expenses - total_emis_baseline
        baseline_dti = (total_emis_baseline / monthly_income) if monthly_income > 0 else None

        # Runway: liquid savings divided by essential outflows (essential expenses + EMIs)
        baseline_essential_outflows = essential_expenses + total_emis_baseline
        baseline_runway = (liquid_savings / baseline_essential_outflows) if baseline_essential_outflows > 0 else None
        
        # Emergency fund gap: target fund = target_months * essential outflows
        baseline_target_fund = baseline_essential_outflows * scenario.emergency_fund_target_months
        baseline_emergency_fund_gap = max(0.0, baseline_target_fund - liquid_savings)

        # Stressed inputs
        stressed_income = max(0.0, monthly_income * (1.0 - scenario.income_reduction_pct / 100.0))
        stressed_essential_expenses = essential_expenses * (1.0 + scenario.essential_expense_surge_pct / 100.0)
        stressed_discretionary_expenses = discretionary_expenses * (1.0 + scenario.discretionary_expense_surge_pct / 100.0)

        # Stressed proposed EMI if rate hike applied
        stressed_proposed_emi = proposed_emi
        if proposed_loan_principal > 0 and proposed_loan_tenure_months > 0 and scenario.interest_rate_hike_pct > 0:
            stressed_rate = proposed_loan_interest_rate + (scenario.interest_rate_hike_pct / 100.0)
            stressed_emi_res = cls.calculate_emi(
                proposed_loan_principal,
                stressed_rate,
                proposed_loan_tenure_months
            )
            stressed_proposed_emi = stressed_emi_res.monthly_emi

        # Explicitly parameterize floating rate sensitivity on existing EMIs (no hidden * 0.5)
        stressed_existing_emis = existing_emis * (1.0 + (scenario.interest_rate_hike_pct / 100.0) * scenario.existing_emi_floating_ratio)

        total_emis_stressed = stressed_existing_emis + stressed_proposed_emi
        stressed_surplus = stressed_income - stressed_essential_expenses - stressed_discretionary_expenses - total_emis_stressed
        stressed_dti = (total_emis_stressed / stressed_income) if stressed_income > 0 else None

        stressed_essential_outflows = stressed_essential_expenses + total_emis_stressed
        stressed_runway = (liquid_savings / stressed_essential_outflows) if stressed_essential_outflows > 0 else None
        
        stressed_target_fund = stressed_essential_outflows * scenario.emergency_fund_target_months
        stressed_emergency_fund_gap = max(0.0, stressed_target_fund - liquid_savings)

        surplus_change = stressed_surplus - baseline_surplus
        runway_change = (stressed_runway - baseline_runway) if (stressed_runway is not None and baseline_runway is not None) else None
        is_insolvent = stressed_surplus < 0

        # Qualitative assessment
        if is_insolvent:
            assessment = "CRITICAL_DEFICIT: Stressed outflows exceed stressed income. Savings depletion risk."
        elif stressed_runway is not None and stressed_runway < 3.0:
            assessment = "VULNERABLE: Positive cash flow but less than 3 months emergency runway under stress."
        elif stressed_dti is not None and stressed_dti > 0.5:
            assessment = "OVERBURDENED: Debt service exceeds 50% of income under stress."
        else:
            assessment = "RESILIENT: Adequate cash buffer and sustainable debt service ratios."

        assumptions = {
            "emergency_fund_target_months": scenario.emergency_fund_target_months,
            "existing_emi_floating_ratio": scenario.existing_emi_floating_ratio,
            "income_reduction_pct": scenario.income_reduction_pct,
            "essential_expense_surge_pct": scenario.essential_expense_surge_pct,
            "discretionary_expense_surge_pct": scenario.discretionary_expense_surge_pct,
            "interest_rate_hike_pct": scenario.interest_rate_hike_pct,
            "planning_buffer_note": "Emergency fund target is a user-configurable planning assumption (default 6 months), not a universal statutory rule."
        }

        return StressTestResult(
            baseline_income=round(monthly_income, 2),
            baseline_essential_expenses=round(essential_expenses, 2),
            baseline_discretionary_expenses=round(discretionary_expenses, 2),
            baseline_existing_emis=round(existing_emis, 2),
            proposed_emi=round(proposed_emi, 2),
            liquid_savings=round(liquid_savings, 2),
            baseline_surplus=round(baseline_surplus, 2),
            baseline_emi_to_income_ratio=round(baseline_dti, 4) if baseline_dti is not None else None,
            baseline_runway_months=round(baseline_runway, 2) if baseline_runway is not None else None,
            baseline_emergency_fund_gap=round(baseline_emergency_fund_gap, 2),
            stressed_income=round(stressed_income, 2),
            stressed_essential_expenses=round(stressed_essential_expenses, 2),
            stressed_discretionary_expenses=round(stressed_discretionary_expenses, 2),
            stressed_existing_emis=round(stressed_existing_emis, 2),
            stressed_proposed_emi=round(stressed_proposed_emi, 2),
            stressed_surplus=round(stressed_surplus, 2),
            stressed_emi_to_income_ratio=round(stressed_dti, 4) if stressed_dti is not None else None,
            stressed_runway_months=round(stressed_runway, 2) if stressed_runway is not None else None,
            stressed_emergency_fund_gap=round(stressed_emergency_fund_gap, 2),
            surplus_change=round(surplus_change, 2),
            runway_change_months=round(runway_change, 2) if runway_change is not None else None,
            is_insolvent=is_insolvent,
            risk_assessment=assessment,
            assumptions=assumptions
        )
