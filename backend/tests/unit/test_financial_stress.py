import pytest
from backend.app.services.financial_stress.engine import (
    EMICalculationResult,
    FinancialStressEngine,
    StressTestScenario,
)


def test_emi_standard_hand_calculated():
    """
    Hand-calculated test:
    Principal P = 100,000
    Annual Rate r = 12% -> monthly r = 0.01
    Tenure n = 12 months
    Formula: 100000 * 0.01 * (1.01)^12 / ((1.01)^12 - 1)
    (1.01)^12 = 1.12682503
    Numerator = 1000 * 1.12682503 = 1126.82503
    Denominator = 0.12682503
    EMI = 8884.88
    """
    res = FinancialStressEngine.calculate_emi(
        principal=100000.0,
        annual_interest_rate=0.12,
        tenure_months=12,
        include_schedule=True
    )
    assert isinstance(res, EMICalculationResult)
    assert abs(res.monthly_emi - 8884.88) < 0.05
    assert abs(res.total_payment - (8884.88 * 12)) < 0.5
    assert len(res.amortization_schedule) == 12
    # Verify final remaining balance is zero
    assert res.amortization_schedule[-1]["remaining_balance"] == 0.0


def test_emi_zero_interest_rate():
    """Edge case: 0% interest loan. EMI = P / n."""
    res = FinancialStressEngine.calculate_emi(
        principal=60000.0,
        annual_interest_rate=0.0,
        tenure_months=12
    )
    assert res.monthly_emi == 5000.0
    assert res.total_interest == 0.0
    assert res.total_payment == 60000.0


def test_emi_invalid_parameters():
    """Boundary validation checks."""
    with pytest.raises(ValueError, match="Principal must be greater than zero"):
        FinancialStressEngine.calculate_emi(principal=0, annual_interest_rate=0.1, tenure_months=12)

    with pytest.raises(ValueError, match="Tenure months must be greater than zero"):
        FinancialStressEngine.calculate_emi(principal=1000, annual_interest_rate=0.1, tenure_months=0)

    with pytest.raises(ValueError, match="Interest rate cannot be negative"):
        FinancialStressEngine.calculate_emi(principal=1000, annual_interest_rate=-0.05, tenure_months=12)


def test_stress_test_surplus_and_runway():
    """
    Hand-calculated stress test:
    Income = 100,000
    Essential = 30,000, Discretionary = 20,000, Existing EMI = 10,000
    Savings = 120,000
    Baseline surplus = 100k - (30k + 20k + 10k) = 40,000
    Essential outflows = 30k + 10k = 40,000
    Baseline runway = 120k / 40k = 3.0 months
    """
    res = FinancialStressEngine.run_stress_test(
        monthly_income=100000.0,
        essential_expenses=30000.0,
        discretionary_expenses=20000.0,
        existing_emis=10000.0,
        liquid_savings=120000.0
    )
    assert res.baseline_surplus == 40000.0
    assert res.baseline_runway_months == 3.0
    assert res.baseline_emi_to_income_ratio == 0.10
    assert not res.is_insolvent


def test_stress_test_under_adverse_shocks():
    """
    Adverse scenario:
    30% income reduction, 20% essential surge.
    Stressed income = 70,000
    Stressed essential = 36,000
    Discretionary = 20,000
    Existing EMI = 10,000
    Stressed surplus = 70k - (36k + 20k + 10k) = 4,000
    """
    scenario = StressTestScenario(
        income_reduction_pct=30.0,
        essential_expense_surge_pct=20.0
    )
    res = FinancialStressEngine.run_stress_test(
        monthly_income=100000.0,
        essential_expenses=30000.0,
        discretionary_expenses=20000.0,
        existing_emis=10000.0,
        liquid_savings=120000.0,
        scenario=scenario
    )
    assert res.stressed_income == 70000.0
    assert res.stressed_essential_expenses == 36000.0
    assert res.stressed_surplus == 4000.0
    assert res.surplus_change == -36000.0
    assert not res.is_insolvent


def test_emergency_fund_gap_hand_calculated():
    """
    Hand-calculated emergency fund gap test:
    Essential expenses = 30,000
    Existing EMIs = 10,000
    Total essential monthly outflows = 30,000 + 10,000 = 40,000
    Emergency target = 6 months
    Target emergency fund = 40,000 * 6 = 240,000
    Liquid savings = 100,000
    Expected emergency fund gap = 240,000 - 100,000 = 140,000
    """
    res = FinancialStressEngine.run_stress_test(
        monthly_income=100000.0,
        essential_expenses=30000.0,
        discretionary_expenses=15000.0,
        existing_emis=10000.0,
        liquid_savings=100000.0,
        scenario=StressTestScenario(emergency_fund_target_months=6.0)
    )
    assert res.baseline_emergency_fund_gap == 140000.0
    assert res.assumptions["emergency_fund_target_months"] == 6.0
    assert "planning_buffer_note" in res.assumptions


def test_boundary_zero_income():
    """
    Boundary test: Zero monthly income (unemployed/pre-revenue).
    Hand calculations:
    Income = 0.0
    Essential = 20,000, Existing EMI = 5,000
    Total outflows = 25,000
    Surplus = 0 - 25,000 = -25,000 (negative surplus)
    DTI = None (safely handles division by zero)
    Runway = 50,000 savings / 25,000 essential outflows = 2.0 months
    Emergency fund target (6 mo) = 25,000 * 6 = 150,000
    Emergency fund gap = 150,000 - 50,000 = 100,000
    """
    res = FinancialStressEngine.run_stress_test(
        monthly_income=0.0,
        essential_expenses=20000.0,
        discretionary_expenses=0.0,
        existing_emis=5000.0,
        liquid_savings=50000.0
    )
    assert res.baseline_income == 0.0
    assert res.baseline_surplus == -25000.0
    assert res.baseline_emi_to_income_ratio is None
    assert res.baseline_runway_months == 2.0
    assert res.baseline_emergency_fund_gap == 100000.0
    assert res.is_insolvent


def test_boundary_zero_expenses_infinite_runway():
    """
    Boundary test: Zero essential and discretionary expenses, zero EMIs.
    Hand calculations:
    Income = 50,000, Outflows = 0.0
    Surplus = 50,000
    Essential outflows = 0 -> Runway is None (avoids division by 0), Gap is 0.0
    """
    res = FinancialStressEngine.run_stress_test(
        monthly_income=50000.0,
        essential_expenses=0.0,
        discretionary_expenses=0.0,
        existing_emis=0.0,
        liquid_savings=10000.0
    )
    assert res.baseline_surplus == 50000.0
    assert res.baseline_runway_months is None
    assert res.baseline_emergency_fund_gap == 0.0
    assert not res.is_insolvent


def test_negative_surplus_and_insolvency():
    """
    Boundary test: Negative surplus when outflows exceed income.
    Hand calculations:
    Income = 30,000
    Essential = 25,000, Discretionary = 10,000, EMIs = 5,000
    Total outflows = 40,000
    Surplus = 30,000 - 40,000 = -10,000 (deficit)
    Savings = 5,000
    Essential outflows = 30,000
    Runway = 5,000 / 30,000 = 0.17 months
    Target emergency fund (6 mo) = 30,000 * 6 = 180,000
    Gap = 180,000 - 5,000 = 175,000
    """
    res = FinancialStressEngine.run_stress_test(
        monthly_income=30000.0,
        essential_expenses=25000.0,
        discretionary_expenses=10000.0,
        existing_emis=5000.0,
        liquid_savings=5000.0
    )
    assert res.baseline_surplus == -10000.0
    assert res.is_insolvent
    assert res.risk_assessment.startswith("CRITICAL_DEFICIT")
    assert res.baseline_emergency_fund_gap == 175000.0

