import json

from backend.app.db.models import StressRun
from backend.app.db.session import get_db
from backend.app.schemas.finance import (
    EMIRequest,
    EMIResponse,
    StressTestRequest,
    StressTestResponse,
)
from backend.app.services.financial_stress.engine import FinancialStressEngine, StressTestScenario
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/finance", tags=["Personal Financial Stress & Affordability"])


@router.post("/emi", response_model=EMIResponse)
def calculate_loan_emi(request: EMIRequest):
    """Compute EMI, total interest, and repayment schedule with deterministic formulas."""
    try:
        result = FinancialStressEngine.calculate_emi(
            principal=request.principal,
            annual_interest_rate=request.annual_interest_rate,
            tenure_months=request.tenure_months,
            include_schedule=request.include_schedule
        )
        return EMIResponse(**result.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/stress-test", response_model=StressTestResponse)
def run_financial_stress_test(request: StressTestRequest, db: Session = Depends(get_db)):
    """Run before/after adverse cash-flow stress test and persist run record."""
    try:
        scenario = StressTestScenario(**request.scenario.model_dump())
        result = FinancialStressEngine.run_stress_test(
            monthly_income=request.monthly_income,
            essential_expenses=request.essential_expenses,
            discretionary_expenses=request.discretionary_expenses,
            existing_emis=request.existing_emis,
            liquid_savings=request.liquid_savings,
            proposed_loan_principal=request.proposed_loan_principal,
            proposed_loan_interest_rate=request.proposed_loan_interest_rate,
            proposed_loan_tenure_months=request.proposed_loan_tenure_months,
            scenario=scenario
        )

        # Persist to database per PRD data model proposal
        stress_run = StressRun(
            input_snapshot_json=json.dumps(request.model_dump()),
            scenario_json=json.dumps(scenario.model_dump()),
            baseline_metrics_json=json.dumps({
                "surplus": result.baseline_surplus,
                "dti": result.baseline_emi_to_income_ratio,
                "runway": result.baseline_runway_months
            }),
            stressed_metrics_json=json.dumps({
                "surplus": result.stressed_surplus,
                "dti": result.stressed_emi_to_income_ratio,
                "runway": result.stressed_runway_months,
                "assessment": result.risk_assessment
            })
        )
        db.add(stress_run)
        db.commit()

        return StressTestResponse(**result.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
