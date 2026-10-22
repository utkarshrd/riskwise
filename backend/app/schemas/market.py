from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class HoldingSchema(BaseModel):
    symbol: str = Field(..., description="Asset ticker symbol, e.g. SPY, AAPL, MSFT, RELIANCE.NS")
    weight: float | None = Field(default=None, description="Portfolio allocation weight (0.0 to 1.0)")
    position_value: float | None = Field(default=None, ge=0.0, description="Optional monetary position value in base currency")


FxMode = Literal["strict", "convert_to_base"]


class FxModeFields(BaseModel):
    """FX handling shared by every request that loads prices. Default is strict single-currency."""

    fx_mode: FxMode = Field(
        default="strict",
        description="'strict' rejects mixed-currency portfolios. 'convert_to_base' converts assets into the portfolio currency using USD/INR history.",
    )
    fx_conversion: bool = Field(
        default=False,
        description="Deprecated alias: true behaves like fx_mode='convert_to_base'.",
    )

    @model_validator(mode="after")
    def _apply_legacy_flag(self):
        if self.fx_conversion and self.fx_mode == "strict":
            self.fx_mode = "convert_to_base"
        return self


class PortfolioAnalyzeRequest(FxModeFields):
    portfolio_name: str = Field(default="My Portfolio", description="Descriptive portfolio identifier")
    currency: str = Field(default="USD", description="Portfolio base currency (single-currency portfolios only)")
    holdings: list[HoldingSchema] = Field(..., min_length=1, description="List of asset holdings with weights or position values")
    portfolio_value: float | None = Field(default=None, gt=0.0, description="Optional total monetary value of portfolio")
    lookback_days: int | None = Field(default=None, ge=30, description="Optional lookback period in days (minimum 30)")
    return_method: str = Field(default="simple", description="'simple' or 'log'")
    var_method: str = Field(default="historical", description="Selected VaR method: 'historical', 'gaussian', 'student_t', 'cornish_fisher', 'ewma', 'monte_carlo', 'garch', 'fhs'")
    horizon_days: int = Field(default=1, ge=1, le=30, description="VaR holding horizon in trading days (default: 1)")
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
    fx: dict[str, Any] | None = None
    chart_series: dict[str, Any] | None = None


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


class PortfolioStressTestRequest(FxModeFields):
    holdings: list[HoldingSchema] = Field(..., min_length=1)
    currency: str | None = Field(default=None, description="Base currency; required when fx_mode is convert_to_base")
    custom_scenarios: list[CustomStressScenarioSchema] | None = Field(default=None)


class StressScenarioResponse(BaseModel):
    scenario_name: str
    portfolio_loss_pct: float
    individual_asset_losses: dict[str, float]
    assumptions: dict[str, Any]


class VaRValidationRequest(FxModeFields):
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
    christoffersen_cc_stat: float | None = None
    christoffersen_cc_p_value: float | None = None
    christoffersen_cc_test_passed: bool | None = None
    basel_capital_multiplier: float | None = 3.00
    summary_message: str
    validation_points: list[dict[str, Any]]
    fx: dict[str, Any] | None = None


class VaRModelComparisonItem(BaseModel):
    method: str
    exceptions: int
    expected_exceptions: float
    exception_rate: float
    expected_exception_rate: float
    basel_zone: str
    basel_capital_multiplier: float
    kupiec_p_value: float | None
    kupiec_test_passed: bool
    christoffersen_ind_p_value: float | None
    christoffersen_ind_passed: bool | None
    christoffersen_cc_p_value: float | None
    christoffersen_cc_test_passed: bool | None
    score: float


class VaRCompareRequest(FxModeFields):
    portfolio_name: str = Field(default="Comparison Portfolio")
    currency: str = Field(default="USD")
    holdings: list[HoldingSchema] = Field(..., min_length=1)
    confidence_level: float = Field(default=0.95, ge=0.80, le=0.999)
    lookback_window: int = Field(default=250, ge=50, description="Rolling estimation window in trading days")
    methods: list[str] | None = Field(
        default=None,
        description="Candidate VaR methods to compare. Defaults to ['historical', 'parametric', 'student_t', 'cornish_fisher', 'ewma'].",
    )


class VaRCompareResponse(BaseModel):
    portfolio_name: str
    currency: str
    confidence_level: float
    lookback_window: int
    forecast_count: int
    models: list[VaRModelComparisonItem]
    recommended_method: str
    recommendation_reason: str
    fx: dict[str, Any] | None = None


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



class StressReplayRequest(FxModeFields):
    holdings: list[HoldingSchema] = Field(..., min_length=1)
    currency: str | None = Field(default=None, description="Portfolio base currency; inferred in strict mode when omitted")
    portfolio_value: float | None = Field(default=None, gt=0.0)
    scenarios: list[str] | None = Field(
        default=None, description="Scenario ids to replay (covid_2020, election_2024, adani_2023). Default: all."
    )


class ReplayContribution(BaseModel):
    symbol: str
    weight: float
    covered_weight_share: float
    start_date: str
    end_date: str
    start_price: float
    end_price: float
    # "return" is a reserved word in Python, exposed under its API name through the alias
    asset_return: float = Field(alias="return")
    trough_return: float
    contribution: float

    model_config = {"populate_by_name": True}


class SkippedHolding(BaseModel):
    symbol: str
    reason: str


class StressReplayScenario(BaseModel):
    id: str
    name: str
    description: str
    window_start: str
    window_end: str
    status: str
    currency: str
    data_source: str
    covered_weight: float
    skipped: list[SkippedHolding]
    contributions: list[ReplayContribution]
    portfolio_return: float | None = None
    portfolio_loss_pct: float | None = None
    portfolio_loss_amount: float | None = None
    fx: dict[str, Any] | None = None


class ReverseStressRequest(FxModeFields):
    holdings: list[HoldingSchema] = Field(..., min_length=1)
    currency: str | None = None
    target_loss_pct: float | None = Field(default=None, gt=0.0, lt=1.0, description="Loss as a fraction of the portfolio, e.g. 0.2 for 20%")
    target_loss_amount: float | None = Field(default=None, gt=0.0, description="Loss in currency units; needs portfolio_value")
    portfolio_value: float | None = Field(default=None, gt=0.0)
    lookback_days: int = Field(default=252, ge=60, le=1000)
    benchmark_symbol: str | None = None


class ReverseStressContribution(BaseModel):
    symbol: str
    weight: float
    beta: float
    shock: float
    contribution: float


class ReverseStressResponse(BaseModel):
    currency: str
    target_loss_pct: float
    target_loss_amount: float | None = None
    uniform_asset_shock: float
    uniform_contributions: list[ReverseStressContribution]
    benchmark_symbol: str
    lookback_observations: int
    lookback_start: str
    lookback_end: str
    portfolio_beta: float
    implied_benchmark_shock: float | None = None
    beta_contributions: list[ReverseStressContribution]
    note: str | None = None
    fx: dict[str, Any] | None = None
