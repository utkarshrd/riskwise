import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from backend.app.core.config import settings
from backend.app.db.models import Instrument, MarketRiskRun, VaRValidationRun
from backend.app.db.session import get_db
from backend.app.schemas.market import (
    MarketRefreshRequest,
    PortfolioAnalyzeRequest,
    PortfolioAnalyzeResponse,
    PortfolioStressTestRequest,
    ReverseStressRequest,
    ReverseStressResponse,
    StockSearchResponse,
    StockSearchResult,
    StressReplayRequest,
    StressReplayScenario,
    StressScenarioResponse,
    SymbolValidateRequest,
    SymbolValidateResponse,
    VaRCompareRequest,
    VaRCompareResponse,
    VaRModelComparisonItem,
    VaRValidationHistoryItem,
    VaRValidationRequest,
    VaRValidationResponse,
)
from backend.app.services.market_risk.engine import Holding, MarketRiskEngine, StressScenario
from backend.app.services.market_risk.market_data_service import MarketDataService
from backend.app.services.market_risk.stress import StressService
from backend.app.services.market_risk.ticker_normalizer import (
    SYMBOL_CATALOGUE,
    get_symbol_currency,
)
from backend.app.services.var_validation.engine import VaRValidationEngine
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/market", tags=["Portfolio Market Risk Lab & VaR Validation"])


@router.get("/universe")
def get_market_universe(limit: int = 100, db: Session = Depends(get_db)):
    """Return available market symbols, data coverage, currency, provenance, and instrument metadata."""
    manifest_file = settings.DATA_DIR / "manifests" / "market_manifest.json"
    snapshots_dir = settings.DATA_DIR / "market_snapshots"

    symbols = []
    symbol_currencies = {}
    if snapshots_dir.exists():
        for f in snapshots_dir.glob("*.csv"):
            if f.stem != "market_snapshot":
                sym = "^NSEI" if f.stem == "_NSEI" else f.stem
                symbols.append(sym)
                symbol_currencies[sym] = get_symbol_currency(sym)

    # Include core symbols from catalogue as well
    for sym_key, meta in SYMBOL_CATALOGUE.items():
        if sym_key not in symbols:
            symbols.append(sym_key)
            symbol_currencies[sym_key] = meta["currency"]

    sectors: set[str] = set()
    cap_buckets: set[str] = set()
    indices: set[str] = set()
    total_instruments = len(symbols)

    try:
        from sqlalchemy import func
        db_count = db.query(func.count(Instrument.symbol)).filter(Instrument.is_active == True).scalar()
        if db_count:
            total_instruments = max(total_instruments, db_count)

        # Distinct facets without full row hydration
        sector_rows = (
            db.query(Instrument.sector)
            .filter(Instrument.is_active == True, Instrument.sector.isnot(None))
            .distinct()
            .all()
        )
        for r in sector_rows:
            if r[0]:
                sectors.add(r[0])

        cap_rows = (
            db.query(Instrument.cap_bucket)
            .filter(Instrument.is_active == True, Instrument.cap_bucket.isnot(None))
            .distinct()
            .all()
        )
        for r in cap_rows:
            if r[0]:
                cap_buckets.add(r[0])

        idx_rows = (
            db.query(Instrument.index_memberships_json)
            .filter(Instrument.is_active == True, Instrument.index_memberships_json.isnot(None))
            .all()
        )
        for r in idx_rows:
            if r[0]:
                try:
                    for idx in json.loads(r[0]):
                        indices.add(idx)
                except Exception:
                    pass

        # If sample needed up to limit, pull lightweight columns (symbol, currency)
        if len(symbols) < limit:
            sample_rows = (
                db.query(Instrument.symbol, Instrument.currency)
                .filter(Instrument.is_active == True)
                .limit(limit)
                .all()
            )
            for sym, curr in sample_rows:
                if sym not in symbols:
                    symbols.append(sym)
                    symbol_currencies[sym] = curr or "INR"
    except Exception:
        pass

    metadata = {
        "provider": "offline_snapshot_with_live_fallback",
        "supported_currencies": ["INR", "USD"],
        "frequency": "daily",
        "price_field": "adj_close",
        "supported_symbols": sorted(symbols),
        "symbol_currencies": symbol_currencies,
        "total_instruments": total_instruments,
        "sectors": sorted(list(sectors)),
        "cap_buckets": sorted(list(cap_buckets)),
        "indices": sorted(list(indices)),
        "manifest_present": manifest_file.exists(),
    }
    return metadata


@router.get("/search", response_model=StockSearchResponse)
def search_market_stocks(
    q: str = "",
    limit: int = 15,
    page: int = 1,
    currency: str | None = None,
    sector: str | None = None,
    index: str | None = None,
    cap_bucket: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Search supported stocks across NSE, BSE, and US markets with sector, index, and cap_bucket filters.
    Returns DB-backed ranked fuzzy search results with pagination.
    """
    service = MarketDataService()
    results, total = service.search_symbols(
        query=q,
        limit=limit,
        page=page,
        currency_hint=currency,
        sector=sector,
        index=index,
        cap_bucket=cap_bucket,
        return_total=True,
        db=db,
    )
    return StockSearchResponse(
        query=q,
        total=total,
        page=page,
        page_size=limit,
        results=[StockSearchResult(**r) for r in results],
    )


@router.post("/validate-symbol", response_model=SymbolValidateResponse)
def validate_market_symbol(request: SymbolValidateRequest):
    """
    Validates a symbol's availability:
    - verified_snapshot: Already available as validated local CSV snapshot
    - live_validated: Retrieved and validated on-the-fly from live market data provider
    - not_available: Quote not found, delisted, insufficient history, or provider error
    """
    service = MarketDataService()
    res = service.validate_symbol(symbol=request.symbol, target_currency=request.target_currency)
    return SymbolValidateResponse(**res)


@router.post("/portfolio/analyze", response_model=PortfolioAnalyzeResponse)
def analyze_portfolio(request: PortfolioAnalyzeRequest, db: Session = Depends(get_db)):
    """Calculate portfolio volatility, historical/parametric VaR, CVaR, and max drawdown."""
    try:
        engine = MarketRiskEngine()
        holdings = [
            Holding(symbol=h.symbol, weight=h.weight, position_value=h.position_value)
            for h in request.holdings
        ]
        metrics = engine.analyze_portfolio(
            holdings=holdings,
            portfolio_name=request.portfolio_name,
            currency=request.currency,
            lookback_days=request.lookback_days,
            return_method=request.return_method,
            portfolio_value=request.portfolio_value,
            var_method=request.var_method,
            horizon_days=request.horizon_days,
            benchmark_symbol=request.benchmark_symbol,
            fx_mode=request.fx_mode,
        )

        # Persist run to database
        risk_run = MarketRiskRun(
            portfolio_snapshot_json=json.dumps(request.model_dump()),
            method="historical_and_parametric",
            confidence_level=0.95,
            lookback=request.lookback_days or metrics.observations_count,
            metrics_json=json.dumps(metrics.model_dump())
        )
        db.add(risk_run)
        db.commit()

        return PortfolioAnalyzeResponse(**metrics.model_dump())
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail={"field": "holdings.symbol", "message": str(e)}) from e
    except ValueError as e:
        msg = str(e)
        field = "holdings.weight" if "weights" in msg.lower() else ("currency" if "currency" in msg.lower() else "lookback_days")
        raise HTTPException(status_code=400, detail={"field": field, "message": msg}) from e


@router.post("/portfolio/stress-test", response_model=list[StressScenarioResponse])
def run_market_stress_test(request: PortfolioStressTestRequest):
    """Run historical and custom factor stress tests against portfolio allocations."""
    try:
        engine = MarketRiskEngine()
        holdings = [
            Holding(symbol=h.symbol, weight=h.weight, position_value=h.position_value)
            for h in request.holdings
        ]
        custom_scenarios = None
        if request.custom_scenarios:
            custom_scenarios = [
                StressScenario(name=s.name, description=s.description, shocks=s.shocks)
                for s in request.custom_scenarios
            ]

        results = engine.run_stress_test(
            holdings=holdings,
            scenarios=custom_scenarios,
            currency=request.currency,
            fx_mode=request.fx_mode,
        )
        return [StressScenarioResponse(**r.model_dump()) for r in results]
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail={"field": "holdings.symbol", "message": str(e)}) from e
    except ValueError as e:
        msg = str(e)
        field = "holdings.weight" if "weights" in msg.lower() else "custom_scenarios"
        raise HTTPException(status_code=400, detail={"field": field, "message": msg}) from e


def get_stress_service() -> StressService:
    """Dependency so tests can swap the price provider."""
    return StressService()


def _holdings(request_holdings) -> list[Holding]:
    return [Holding(symbol=h.symbol, weight=h.weight, position_value=h.position_value) for h in request_holdings]


@router.post("/portfolio/stress/replay", response_model=list[StressReplayScenario], response_model_by_alias=True)
def replay_named_stress_scenarios(request: StressReplayRequest, service: StressService = Depends(get_stress_service)):
    """
    Replay named historical events (COVID Feb-Mar 2020, 4 Jun 2024 election day, Adani Jan-Feb 2023) against the
    portfolio using real prices. Holdings with no data in a window are skipped and listed, never filled in.
    """
    try:
        return service.replay(
            holdings=_holdings(request.holdings),
            currency=request.currency,
            fx_mode=request.fx_mode,
            scenario_ids=request.scenarios,
            portfolio_value=request.portfolio_value,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail={"field": "holdings.symbol", "message": str(e)}) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"field": "scenarios", "message": str(e)}) from e


@router.post("/portfolio/stress/reverse", response_model=ReverseStressResponse)
def reverse_stress_test(request: ReverseStressRequest, service: StressService = Depends(get_stress_service)):
    """The uniform shock, and the benchmark fall at the portfolio's beta, that produce a given portfolio loss."""
    try:
        return service.reverse(
            holdings=_holdings(request.holdings),
            currency=request.currency,
            target_loss_pct=request.target_loss_pct,
            target_loss_amount=request.target_loss_amount,
            portfolio_value=request.portfolio_value,
            fx_mode=request.fx_mode,
            lookback_days=request.lookback_days,
            benchmark_symbol=request.benchmark_symbol,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail={"field": "holdings.symbol", "message": str(e)}) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"field": "target_loss_pct", "message": str(e)}) from e


@router.post("/var/validate", response_model=VaRValidationResponse)
def validate_var_model(request: VaRValidationRequest, db: Session = Depends(get_db)):
    """Perform rolling out-of-sample VaR validation with Kupiec and Christoffersen tests."""
    try:
        val_engine = VaRValidationEngine()
        holdings = [
            Holding(symbol=h.symbol, weight=h.weight, position_value=h.position_value)
            for h in request.holdings
        ]
        result = val_engine.run_rolling_backtest(
            holdings=holdings,
            portfolio_name=request.portfolio_name,
            currency=request.currency,
            method=request.method,
            confidence_level=request.confidence_level,
            lookback_window=request.lookback_window,
            fx_mode=request.fx_mode,
        )

        # Persist validation run
        val_run = VaRValidationRun(
            portfolio_snapshot_json=json.dumps(request.model_dump()),
            method=request.method,
            confidence_level=request.confidence_level,
            lookback=request.lookback_window,
            forecast_count=result.forecast_count,
            exception_count=result.exception_count,
            exception_rate=result.exception_rate,
            results_path="in_memory_run"
        )
        db.add(val_run)
        db.flush()

        # Save run summary artifact
        artifacts_dir = settings.ARTIFACTS_DIR / "var_validation"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifacts_dir / f"{val_run.id}.json"
        run_summary = {
            "id": val_run.id,
            "created_at": datetime.now(UTC).isoformat(),
            "portfolio_name": result.portfolio_name,
            "currency": result.currency,
            "method": result.method,
            "confidence_level": result.confidence_level,
            "lookback_window": result.lookback_window,
            "forecast_count": result.forecast_count,
            "exception_count": result.exception_count,
            "exception_rate": result.exception_rate,
            "expected_exception_rate": result.expected_exception_rate,
            "basel_zone": result.basel_zone,
            "basel_zone_cumulative_prob": result.basel_zone_cumulative_prob,
            "kupiec_lr_stat": result.kupiec_lr_stat,
            "kupiec_p_value": result.kupiec_p_value,
            "kupiec_test_passed": result.kupiec_test_passed,
            "christoffersen_lr_stat": result.christoffersen_lr_stat,
            "christoffersen_p_value": result.christoffersen_p_value,
            "christoffersen_test_passed": result.christoffersen_test_passed,
            "christoffersen_cc_stat": result.christoffersen_cc_stat,
            "christoffersen_cc_p_value": result.christoffersen_cc_p_value,
            "christoffersen_cc_test_passed": result.christoffersen_cc_test_passed,
            "summary_message": result.summary_message,
            "symbols": [h.symbol for h in holdings],
        }
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(run_summary, f, indent=2)

        val_run.results_path = f"artifacts/var_validation/{val_run.id}.json"
        db.commit()

        return VaRValidationResponse(
            portfolio_name=result.portfolio_name,
            currency=result.currency,
            method=result.method,
            confidence_level=result.confidence_level,
            lookback_window=result.lookback_window,
            n_obs=result.n_obs,
            window=result.window,
            confidence=result.confidence,
            exceptions=result.exceptions,
            expected_exceptions=result.expected_exceptions,
            forecast_count=result.forecast_count,
            exception_count=result.exception_count,
            exception_rate=result.exception_rate,
            expected_exception_rate=result.expected_exception_rate,
            basel_zone=result.basel_zone,
            basel_zone_cumulative_prob=result.basel_zone_cumulative_prob,
            kupiec_lr_stat=result.kupiec_lr_stat,
            kupiec_p_value=result.kupiec_p_value,
            kupiec_test_passed=result.kupiec_test_passed,
            christoffersen_lr_stat=result.christoffersen_lr_stat,
            christoffersen_p_value=result.christoffersen_p_value,
            christoffersen_test_passed=result.christoffersen_test_passed,
            christoffersen_cc_stat=result.christoffersen_cc_stat,
            christoffersen_cc_p_value=result.christoffersen_cc_p_value,
            christoffersen_cc_test_passed=result.christoffersen_cc_test_passed,
            summary_message=result.summary_message,
            validation_points=[p.model_dump() for p in result.validation_points],
            fx=result.fx,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail={"field": "holdings.symbol", "message": str(e)}) from e
    except ValueError as e:
        msg = str(e)
        field = "holdings.weight" if "weights" in msg.lower() else "lookback_window"
        raise HTTPException(status_code=400, detail={"field": field, "message": msg}) from e


@router.get("/var/history", response_model=list[VaRValidationHistoryItem])
def get_var_validation_history(limit: int = 20, db: Session = Depends(get_db)):
    """Retrieve historical rolling VaR validation runs with Kupiec and Basel statistics."""
    runs = db.query(VaRValidationRun).order_by(VaRValidationRun.created_at.desc()).limit(limit).all()
    history = []
    for r in runs:
        symbols = []
        portfolio_name = "Validation Portfolio"
        currency = "USD"
        try:
            snap = json.loads(r.portfolio_snapshot_json)
            portfolio_name = snap.get("portfolio_name", "Validation Portfolio")
            currency = snap.get("currency", "USD")
            symbols = [h.get("symbol", "") for h in snap.get("holdings", [])]
        except (json.JSONDecodeError, AttributeError):
            pass

        basel_zone = None
        kupiec_p_val = None
        kupiec_passed = None
        christoffersen_p_val = None
        christoffersen_passed = None
        if r.results_path:
            artifact_file = settings.REPO_ROOT / r.results_path if not Path(r.results_path).is_absolute() else Path(r.results_path)
            if artifact_file.exists():
                try:
                    with open(artifact_file, "r", encoding="utf-8") as f:
                        saved_data = json.load(f)
                        basel_zone = saved_data.get("basel_zone")
                        kupiec_p_val = saved_data.get("kupiec_p_value")
                        kupiec_passed = saved_data.get("kupiec_test_passed")
                        christoffersen_p_val = saved_data.get("christoffersen_p_value")
                        christoffersen_passed = saved_data.get("christoffersen_test_passed")
                except (OSError, json.JSONDecodeError):
                    pass

        history.append(
            VaRValidationHistoryItem(
                id=r.id,
                created_at=r.created_at.isoformat() if r.created_at else "",
                portfolio_name=portfolio_name,
                currency=currency,
                symbols=symbols,
                method=r.method,
                confidence_level=r.confidence_level,
                lookback=r.lookback,
                forecast_count=r.forecast_count,
                exception_count=r.exception_count,
                exception_rate=r.exception_rate,
                expected_exception_rate=round(1.0 - r.confidence_level, 4),
                basel_zone=basel_zone,
                kupiec_p_value=kupiec_p_val,
                kupiec_test_passed=kupiec_passed,
                christoffersen_p_value=christoffersen_p_val,
                christoffersen_test_passed=christoffersen_passed,
            )
        )
    return history


@router.post("/var/compare", response_model=VaRCompareResponse)
def var_model_compare(
    request: VaRCompareRequest,
    db: Session = Depends(get_db),
):
    """
    Side-by-side VaR model comparison using rolling backtests.

    Runs the same rolling out-of-sample backtest for each candidate model
    (historical, parametric, student_t, cornish_fisher, ewma by default, or
    the list provided via the `methods` query parameter) and returns a ranked
    scorecard plus a plain-English model recommendation.

    Scoring penalises deviation from the expected exception rate, Basel
    YELLOW/RED zones, Kupiec POF test failure, and Christoffersen conditional
    coverage failure.
    """
    validation_engine = VaRValidationEngine()
    holdings = [
        Holding(
            symbol=h.symbol,
            weight=h.weight,
            position_value=h.position_value,
        )
        for h in request.holdings
    ]
    try:
        result = validation_engine.compare_models(
            holdings=holdings,
            portfolio_name=request.portfolio_name,
            currency=request.currency,
            confidence_level=request.confidence_level,
            lookback_window=request.lookback_window,
            methods=request.methods,
            fx_mode=request.fx_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return VaRCompareResponse(
        portfolio_name=result["portfolio_name"],
        currency=result["currency"],
        confidence_level=result["confidence_level"],
        lookback_window=result["lookback_window"],
        forecast_count=result["forecast_count"],
        models=[
            VaRModelComparisonItem(**m)
            for m in result["models"]
        ],
        recommended_method=result["recommended_method"],
        recommendation_reason=result["recommendation_reason"],
        fx=result.get("fx"),
    )


@router.post("/refresh")
def refresh_market_data(request: MarketRefreshRequest | None = None):
    """
    Refreshes market data manifest and verifies price snapshot availability, row counts, and date ranges.
    Supports live retrieval via yfinance with automatic graceful fallback to snapshot.
    """
    service = MarketDataService()
    if request and request.fetch_live:
        res = service.refresh_symbols(target_symbols=request.symbols)
        return {
            "status": res["status"],
            "data_source_mode": res["data_source_mode"],
            "live_error": None if not res["errors"] else str(res["errors"]),
            "provider": "yfinance",
            "currency": "USD/INR",
            "supported_symbols": res["supported_symbols"],
            "snapshot_details": res["snapshot_details"],
            "refreshed_symbols": res["refreshed_symbols"],
            "manifest_present": (settings.DATA_DIR / "manifests" / "market_manifest.json").exists(),
            "refreshed_at": res["refreshed_at"],
        }

    # Offline snapshot audit
    manifest_file = settings.DATA_DIR / "manifests" / "market_manifest.json"
    snapshots_dir = settings.DATA_DIR / "market_snapshots"
    snapshot_counts = {}
    if snapshots_dir.exists():
        for f in snapshots_dir.glob("*.csv"):
            if f.stem != "market_snapshot":
                try:
                    df = pd.read_csv(f)
                    date_col = next((c for c in df.columns if c.lower() == "date"), None)
                    price_col = next((c for c in df.columns if c.lower() in ["adj_close", "adj close", "close"]), None)
                    snapshot_counts[f.stem] = {
                        "row_count": len(df),
                        "start_date": str(df[date_col].min()) if date_col and not df.empty else None,
                        "end_date": str(df[date_col].max()) if date_col and not df.empty else None,
                        "price_column": price_col,
                    }
                except (OSError, ValueError, KeyError) as e:
                    snapshot_counts[f.stem] = {"error": str(e)}

    return {
        "status": "ok",
        "data_source_mode": "offline_snapshot",
        "live_error": None,
        "provider": "offline_snapshot",
        "currency": "USD/INR",
        "supported_symbols": sorted(snapshot_counts.keys()),
        "snapshot_details": snapshot_counts,
        "manifest_present": manifest_file.exists(),
        "refreshed_at": datetime.now(UTC).isoformat()
    }
