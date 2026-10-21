import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["Methodology & Disclosures"])

_REPO_ROOT = Path(__file__).resolve().parents[4]


class MethodologyResponse(BaseModel):
    platform: str
    version: str
    credit_risk_methodology: dict
    market_risk_conventions: dict
    financial_calculations: dict
    disclaimers: list[str]


class IndiaContextCard(BaseModel):
    topic: str
    publisher: str
    url: str
    access_date: str
    summary: str
    disclaimer: str


@router.get("/methodology", response_model=MethodologyResponse)
def get_methodology_disclosures():
    """Return scientific conventions, calculation formulas, and legal disclosures."""
    return MethodologyResponse(
        platform="RiskWise Multi-Domain Financial Risk Intelligence Platform",
        version="3.0.0",
        credit_risk_methodology={
            "dataset": (
                "Indian Banking and CIBIL Bureau Dataset — merged from Internal_Bank_Dataset.xlsx "
                "and External_Cibil_Dataset.xlsx on PROSPECTID (51,336 records)."
            ),
            "target_variable": (
                "Approved_Flag (P1, P2, P3, P4) — four-tier credit category labels "
                "present in the External CIBIL bureau dataset."
            ),
            "category_note": (
                "P1–P4 are the original Approved_Flag column labels from the dataset. "
                "They do NOT correspond to regulated CIBIL score bands "
                "or any official Indian default classification."
            ),
            "split": "70% train / 15% validation / 15% test, stratified by Approved_Flag, random_state=42.",
            "algorithms": [
                "Majority Class Baseline (most-frequent strategy)",
                "Multinomial Logistic Regression (max_iter=1000, random_state=42)",
                "XGBoost Multiclass — Champion: 42 features, Credit_Score excluded",
                "XGBoost Leakage Study: 43 features including Credit_Score (comparison only)"
            ],
            "champion_model": (
                "XGBoost Multiclass (200 estimators, depth 5, lr 0.08) trained on 42 features. "
                "Credit_Score is excluded from production inference to prevent target leakage."
            ),
            "explainability": (
                "TreeSHAP per-record feature attribution. Computed at inference time from the "
                "actual model artifact and submitted feature values. No pre-computed or fabricated contributions."
            ),
            "proxy_nature": (
                "Educational classifier. Outputs are relative historical credit categories "
                "from this specific dataset. Not a CIBIL score estimator, not a loan approval engine, "
                "not a calibrated Indian probability of default."
            ),
        },
        market_risk_conventions={
            "annualization_factor": 252,
            "return_type": "Daily simple returns from adjusted closing prices",
            "loss_convention": "Loss is positive magnitude (Loss = −Return)",
            "var_confidence_levels": [0.95, 0.99],
            "var_models": [
                "Historical empirical percentile",
                "Parametric normal distribution"
            ],
            "expected_shortfall": "Mean tail loss beyond VaR cutoff",
            "backtesting_protocol": (
                "Rolling out-of-sample trailing estimation window. "
                "Kupiec POF likelihood-ratio test (chi-sq, df=1). "
                "Christoffersen independence test (chi-sq, df=1). "
                "Basel traffic-light zone from cumulative binomial CDF."
            ),
        },
        financial_calculations={
            "emi_formula": "P × r × (1+r)^n / ((1+r)^n − 1) for r > 0; P / n for r = 0",
            "dti_formula": "total_monthly_emis / monthly_income",
            "runway_formula": "liquid_savings / (essential_expenses + total_emis)",
            "currency": "INR",
        },
        disclaimers=[
            "RiskWise is an educational and engineering research prototype, not a lending decision engine.",
            (
                "The P1–P4 tiers are the original Approved_Flag column labels from the training dataset. "
                "They are relative historical classifications within this dataset and do NOT estimate "
                "Indian CIBIL credit scores, regulated risk categories, or calibrated default probabilities."
            ),
            "Value at Risk (VaR) does NOT represent maximum conceivable loss; extreme tail events may exceed VaR.",
            "The platform does not provide regulated personal wealth, investment, tax, or legal advice.",
            "SHAP contributions show model sensitivity under the fitted model, not causal credit impact.",
        ],
    )


@router.get("/methodology/model-comparison")
def get_model_comparison():
    """Serve actual model comparison evaluation artifact generated by the training pipeline."""
    # Prefer the Indian-dataset specific comparison if available
    indian_path = _REPO_ROOT / "artifacts" / "evaluation" / "indian_credit_model_comparison.json"
    general_path = _REPO_ROOT / "artifacts" / "evaluation" / "model_comparison.json"

    comp_path = indian_path if indian_path.exists() else (general_path if general_path.exists() else None)
    if comp_path is None:
        raise HTTPException(
            status_code=404,
            detail="Model comparison artifact not found. Run ml/train.py to generate it."
        )

    with open(comp_path, encoding="utf-8") as f:
        comparisons = json.load(f)

    return {
        "source": str(comp_path.relative_to(_REPO_ROOT)),
        "note": (
            "Metrics evaluated on the held-out 15% stratified test partition. "
            "Champion XGBoost excludes Credit_Score to prevent target leakage. "
            "The leakage study model (xgboost_with_credit_score) is included for comparison only "
            "and is NOT used for production scoring."
        ),
        "comparisons": comparisons,
    }


@router.get("/methodology/india-context", response_model=list[IndiaContextCard])
def get_india_context_cards():
    """
    Return sourced India financial-literacy and policy context cards from the curated RAG corpus.
    These cards are served separately from ML outputs and must not be mixed with model predictions.
    """
    manifest_path = _REPO_ROOT / "knowledge" / "manifest.csv"
    sources_dir = _REPO_ROOT / "knowledge" / "sources"

    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Knowledge corpus manifest not found.")

    cards: list[IndiaContextCard] = []
    try:
        import csv

        with open(manifest_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                filename = row.get("filename", "")
                source_file = sources_dir / filename if filename else None
                snippet = ""
                if source_file and source_file.exists():
                    with open(source_file, encoding="utf-8") as sf:
                        for line in sf:
                            stripped = line.strip()
                            if stripped and not stripped.startswith("#"):
                                snippet = stripped[:500]
                                break

                cards.append(
                    IndiaContextCard(
                        topic=row.get("title", filename),
                        publisher=row.get("publisher", ""),
                        url=row.get("url", ""),
                        access_date=row.get("access_date", row.get("retrieval_date", "")),
                        summary=snippet or row.get("description", ""),
                        disclaimer=(
                            "This information is sourced from official or academic publications "
                            "and is shown for educational context only. "
                            "It does not modify ML model outputs and is not financial advice."
                        ),
                    )
                )
    except (OSError, csv.Error) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load context manifest: {exc}") from exc

    return cards
