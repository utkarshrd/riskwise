import json

from backend.app.core.config import settings
from backend.app.db.models import AssessmentRun, ModelVersion
from backend.app.db.session import get_db
from backend.app.schemas.credit import (
    BorrowerProfileSample,
    CreditExplainRequest,
    CreditExplainResponse,
    CreditModelMetadata,
    CreditProfileScoreRequest,
    CreditScoreRequest,
    CreditScoreResponse,
    WhatIfRequest,
    WhatIfResponse,
)
from backend.app.services.credit.service import (
    SAMPLE_PROFILES,
    CreditService,
    map_profile_to_features,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

router = APIRouter(prefix="/credit", tags=["Credit Risk Intelligence"])


@router.get("/models", response_model=list[CreditModelMetadata])
def list_credit_models(db: Session = Depends(get_db)):
    """List trained credit model versions and actual real evaluation metadata."""
    models = db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).all()
    results = []
    for m in models:
        metrics = json.loads(m.metrics_json) if m.metrics_json else {}
        results.append(CreditModelMetadata(
            id=m.id,
            model_name=m.model_name,
            version=m.version,
            dataset_id=m.dataset_id,
            status=m.status,
            trained_at=m.trained_at.isoformat(),
            checksum=m.checksum,
            metrics=metrics
        ))
    return results


@router.get("/samples", response_model=list[BorrowerProfileSample])
def get_sample_borrower_profiles():
    """Returns safe, non-sensitive reference demonstration borrower profiles across P1-P4 tiers."""
    return [BorrowerProfileSample(**p) for p in SAMPLE_PROFILES]


@router.post("/profile-score", response_model=CreditScoreResponse)
def score_borrower_profile(request: CreditProfileScoreRequest, db: Session = Depends(get_db)):
    """Score plain input profile (income, tenure, payment amounts, and late status) and persist run."""
    try:
        service = CreditService(db)
        if not service.active_model_version:
            raise HTTPException(status_code=503, detail="No active credit model artifact registered.")

        features = map_profile_to_features(
            credit_limit=request.credit_limit,
            bill_amounts=request.bill_amounts,
            payment_amounts=request.payment_amounts,
            months_late=request.months_late,
            age=request.age,
            net_monthly_income=request.net_monthly_income,
            time_with_curr_empr=request.time_with_curr_empr,
            marital_status=request.marital_status,
            education=request.education,
            gender=request.gender
        )
        result = service.score(features)

        # Persist assessment run
        assessment = AssessmentRun(
            model_version_id=service.active_model_version.id,
            input_snapshot_json=json.dumps(features, default=str),
            score=result.probability_of_default,
            risk_band=result.relative_risk_band,
            warnings_json=json.dumps(result.warnings)
        )
        db.add(assessment)
        db.commit()

        return CreditScoreResponse(**result.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/score", response_model=CreditScoreResponse)
def score_borrower(request: CreditScoreRequest, db: Session = Depends(get_db)):
    """Score borrower feature attributes, return predicted tier and class probabilities."""
    try:
        service = CreditService(db)
        if not service.active_model_version:
            raise HTTPException(status_code=503, detail="No active credit model artifact registered.")

        result = service.score(request.features)

        # Persist assessment run
        assessment = AssessmentRun(
            model_version_id=service.active_model_version.id,
            input_snapshot_json=json.dumps(request.features, default=str),
            score=result.probability_of_default,
            risk_band=result.relative_risk_band,
            warnings_json=json.dumps(result.warnings)
        )
        db.add(assessment)
        db.commit()

        return CreditScoreResponse(**result.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/explain", response_model=CreditExplainResponse)
def explain_credit_score(request: CreditExplainRequest, db: Session = Depends(get_db)):
    """Compute local SHAP feature contributions for borrower profile."""
    try:
        service = CreditService(db)
        if not service.active_model_version:
            raise HTTPException(status_code=503, detail="No active credit model artifact registered.")

        result = service.explain(request.features, top_n=request.top_n)
        return CreditExplainResponse(
            model_version=result.model_version,
            predicted_category=result.predicted_category,
            class_probabilities=result.class_probabilities,
            probability_of_default=result.probability_of_default,
            base_value=result.base_value,
            top_contributions=[c.model_dump() for c in result.top_contributions],
            all_contributions=result.all_contributions
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/what-if", response_model=WhatIfResponse)
def what_if_counterfactual(
    request: WhatIfRequest,
    actionable: bool = Query(default=False, description="Enforce actionable-only mode and return ranked changes"),
    db: Session = Depends(get_db)
):
    """Re-score baseline profile with modified features and compare category & probability shifts."""
    try:
        service = CreditService(db)
        if not service.active_model_version:
            raise HTTPException(status_code=503, detail="No active credit model artifact registered.")

        is_actionable = request.actionable_only or actionable
        result = service.what_if(
            request.baseline_features,
            request.modifications,
            actionable_only=is_actionable
        )
        return WhatIfResponse(**result.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/model-comparison")
def get_credit_model_comparison():
    """Returns the trained credit model comparison evaluation artifact and leakage study."""
    indian_path = settings.REPO_ROOT / "artifacts" / "evaluation" / "indian_credit_model_comparison.json"
    general_path = settings.REPO_ROOT / "artifacts" / "evaluation" / "model_comparison.json"
    comp_path = indian_path if indian_path.exists() else (general_path if general_path.exists() else None)

    if not comp_path:
        raise HTTPException(status_code=404, detail="Model comparison evaluation artifact not found.")

    with open(comp_path, encoding="utf-8") as f:
        comparisons = json.load(f)

    return comparisons


@router.get("/assessments/export")
def export_credit_assessments(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Exports recent credit assessment runs in JSON or CSV format (FR-REP-01).
    """
    assessments = db.query(AssessmentRun).order_by(AssessmentRun.created_at.desc()).limit(limit).all()

    records = []
    for a in assessments:
        inp = {}
        if a.input_snapshot_json:
            try:
                inp = json.loads(a.input_snapshot_json)
            except (json.JSONDecodeError, TypeError):
                inp = {}
        records.append({
            "id": a.id,
            "model_version_id": a.model_version_id,
            "risk_band": a.risk_band,
            "score": a.score,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            **{f"feature_{k}": v for k, v in inp.items()}
        })

    if format == "json":
        return {
            "total_exported": len(records),
            "format": "json",
            "assessments": records
        }

    # CSV Export
    import csv
    import io

    output = io.StringIO()
    if records:
        fieldnames = []
        for r in records:
            for k in r:
                if k not in fieldnames:
                    fieldnames.append(k)
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    else:
        writer = csv.writer(output)
        writer.writerow(["id", "model_version_id", "risk_band", "score", "created_at"])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=credit_assessments.csv"}
    )
