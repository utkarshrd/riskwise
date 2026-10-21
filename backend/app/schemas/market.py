from typing import Any

from pydantic import BaseModel, Field


class HoldingSchema(BaseModel):
    symbol: str = Field(..., description="Asset ticker symbol, e.g. SPY, AAPL, MSFT, RELIANCE.NS")
    weight: float | None = Field(default=None, description="Portfolio allocation weight (0.0 to 1.0)")
    position_value: float | None = Field(default=None, ge=0.0, description="Optional monetary position value in base currency")


class PortfolioAnalyzeRequest(BaseModel):
    portfolio_name: str = Field(default="My Portfolio", description="Descriptive portfolio identifier")
    currency: str = Field(default="USD", description="Portfolio base currency (single-currency portfolios only)")
    holdings: list[HoldingSchema] = Field(..., min_length=1, description="List of asset holdings with weights or position values")
    portfolio_value: float | None = Field(default=None, gt=0.0, description="Optional total monetary value of portfolio")
    lookback_days: int | None = Field(default=None, ge=30, description="Optional lookback period in days (minimum 30)")
    return_method: str = Field(default="simple", description="'simple' or 'log'")
    var_method: str = Field(default="historical", description="Selected VaR method: 'historical', 'gaussian', 'student_t', 'cornish_fisher', 'ewma', 'monte_carlo', 'garch', 'fhs'")
    horizon_days: int = Field(default=1, ge=1, le=30, description="VaR holding horizon in trading days (default: 1)")
    fx_conversion: bool = Field(default=False, description="Explicit opt-in to convert mixed-currency assets using historical FX rates")
    benchmark_symbol: str | None = Field(default=None, description="Optional custom benchmark symbol (defaults to ^NSEI for INR, SPY for USD)")


class PortfolioAnalyzeResponse(BaseModel):
    portfolio_name: str
    currency: str
    symbols: list[str]
    weights: list[float]
    portfolio_value: float | None = None
    position_values: dict[str, float] | None = None
    observations_count: int
    start_date: str
    end_date: str
    data_source_mode: str = "offline_snapshot"
    annualized_volatility: float
    annualization_factor: int = 252
    historical_var_95: float
    historical_var_99: float
    parametric_var_95: float
    parametric_var_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    historical_var_95_amount: float | None = None
    historical_var_99_amount: float | None = None
    parametric_var_95_amount: float | None = None
    parametric_var_99_amount: float | None = None
    expected_shortfall_95_amount: float | None = None
    expected_shortfall_99_amount: float | None = None
    maximum_drawdown: float
    mean_daily_return: float
    asset_correlations: dict[str, dict[str, float]]
    loss_convention: str
    assumptions: dict[str, Any]
    selected_var_method: str = "historical"
    horizon_days: int = 1
    selected_var_95: float | None = None
    selected_var_99: float | None = None
    selected_es_95: float | None = None
    selected_es_99: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    drawdown_table: list[dict[str, Any]] | None = None
    component_var_pct: dict[str, float] | None = None
    marginal_var: dict[str, float] | None = None
    benchmark_symbol: str | None = None
    benchmark_name: str | None = None
    benchmark_volatility: float | None = None
    beta_to_benchmark: float | None = None
    correlation_to_benchmark: float | None = None
    fx_converted: bool = False
    data_freshness: dict[str, Any] | None = None


class MarketRefreshRequest(BaseModel):
    fetch_live: bool = Field(default=False, description="Attempt live download from Yahoo Finance via yfinance if true")
    symbols: list[str] | None = Field(default=None, description="Optional subset of symbols to refresh")


class MarketRefreshStatusResponse(BaseModel):
    status: str
    job_id: str | None = None
    refreshed_symbols: list[str] = []
    errors: dict[str, str] = {}
    last_refresh: str | None = None


class VaRValidationHistoryItem(BaseModel):
    id: str
    created_at: str
    portfolio_name: str
    currency: str
    symbols: list[str]
    method: str
    confidence_level: float
    lookback: int
    forecast_count: int
    exception_count: int
    exception_rate: float
    expected_exception_rate: float
    basel_zone: str | None = None
    kupiec_p_value: float | None = None
    kupiec_test_passed: bool | None = None
    christoffersen_p_value: float | None = None
    christoffersen_test_passed: bool | None = None


class CustomStressScenarioSchema(BaseModel):
    name: str = Field(..., description="Scenario identifier")
    description: str = Field(..., description="Scenario description and macroeconomic assumptions")
    shocks: dict[str, float] = Field(..., description="Per-symbol percentage shocks, e.g. {'AAPL': -0.25}")


class PortfolioStressTestRequest(BaseModel):
    holdings: list[HoldingSchema] = Field(..., min_length=1)
    custom_scenarios: list[CustomStressScenarioSchema] | None = Field(default=None)


class StressScenarioResponse(BaseModel):
    scenario_name: str
    portfolio_loss_pct: float
    individual_asset_losses: dict[str, float]
    assumptions: dict[str, Any]


class VaRValidationRequest(BaseModel):
    portfolio_name: str = Field(default="Validation Portfolio")
    currency: str = Field(default="USD")
    holdings: list[HoldingSchema] = Field(..., min_length=1)
    method: str = Field(default="historical", description="'historical' or 'parametric'")
    confidence_level: float = Field(default=0.95, ge=0.80, le=0.999)
    lookback_window: int = Field(default=250, ge=50, description="Rolling estimation window in trading days")


class VaRValidationResponse(BaseModel):
    portfolio_name: str
    currency: str
    method: str
    confidence_level: float
    lookback_window: int
    n_obs: int
    window: int
    confidence: float
    exceptions: int
    expected_exceptions: float
    forecast_count: int
    exception_count: int
    exception_rate: float
    expected_exception_rate: float
    basel_zone: str
    basel_zone_cumulative_prob: float
    kupiec_lr_stat: float | None
    kupiec_p_value: float | None
    kupiec_test_passed: bool
    christoffersen_lr_stat: float | None
    christoffersen_p_value: float | None
    christoffersen_test_passed: bool | None
    summary_message: str
    validation_points: list[dict[str, Any]]


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str
    currency: str
    is_cached: bool = False
    status: str = "known"  # 'verified', 'known', 'valid_remote'
    alias_of: str | None = None
    note: str | None = None
    isin: str | None = None
    sector: str | None = None
    industry: str | None = None
    cap_bucket: str | None = None
    index_memberships: list[str] | None = None


class StockSearchResponse(BaseModel):
    query: str
    total: int = 0
    page: int = 1
    page_size: int = 15
    results: list[StockSearchResult]


class SymbolValidateRequest(BaseModel):
    symbol: str = Field(..., description="Candidate symbol to validate (e.g. ADANIENT, RELIANCE, ZOMATO)")
    target_currency: str | None = Field(default=None, description="Optional target currency hint (INR or USD)")


class SymbolValidateResponse(BaseModel):
    symbol: str
    canonical_symbol: str
    name: str
    exchange: str
    currency: str
    state: str  # 'verified_snapshot', 'live_validated', 'not_available'
    is_cached: bool
    observations_count: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    alias_note: str | None = None
    error_reason: str | None = None
    message: str

