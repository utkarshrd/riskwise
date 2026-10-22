// RiskWise API client - connects to FastAPI backend at localhost:8000

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(0, `Cannot reach the RiskWise API at ${BASE_URL}. Check that the backend is running.`);
  }
  if (!res.ok) {
    throw new ApiError(res.status, await readErrorMessage(res));
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Pull the human-readable part out of FastAPI error bodies ({"detail": "..."} or {"detail": {"message": "..."}}). */
async function readErrorMessage(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const detail = JSON.parse(text)?.detail;
    if (typeof detail === "string") return detail;
    if (detail?.message) return String(detail.message);
    if (Array.isArray(detail)) {
      return detail.map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.slice(1).join(".") ?? ""} ${d.msg ?? ""}`.trim()).join("; ");
    }
  } catch {
    // not JSON; fall through to the raw body
  }
  return text ? `Request failed (${res.status}): ${text.slice(0, 300)}` : `Request failed (${res.status}).`;
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  timestamp: string;
}

export interface SystemStatus {
  status: string;
  offline_mode: boolean;
  credit_model_loaded: boolean;
  active_model_version: string | null;
  market_snapshot_loaded: boolean;
  market_tickers_available: string[];
  rag_corpus_loaded: boolean;
}

export interface CreditModelMetadata {
  id: string;
  model_name: string;
  version: string;
  dataset_id: string;
  status: string;
  trained_at: string;
  checksum: string;
  metrics: Record<string, number | string | number[][]>;
}

export interface FeatureContribution {
  feature_name: string;
  feature_value: number;
  shap_value: number;
  impact_direction: string;
}

export interface BorrowerProfileSample {
  sample_id: string;
  label: string;
  description: string;
  expected_category: string;
  features: Record<string, string | number>;
}

export interface CreditScoreResponse {
  model_version: string;
  predicted_category: string;
  class_probabilities: Record<string, number>;
  probability_of_default: number;
  relative_risk_score?: number;
  relative_risk_band: string;
  percentile_framing: string;
  warnings: string[];
  methodology_disclosure: string;
  proxy_dataset_disclaimer?: string;
}

export interface CreditExplainResponse {
  model_version: string;
  predicted_category: string;
  class_probabilities: Record<string, number>;
  probability_of_default: number;
  base_value: number;
  top_contributions: FeatureContribution[];
  all_contributions: Record<string, number>;
}

export interface WhatIfResponse {
  baseline_category?: string;
  counterfactual_category?: string;
  baseline_probabilities?: Record<string, number>;
  counterfactual_probabilities?: Record<string, number>;
  baseline_probability: number;
  baseline_risk_band: string;
  counterfactual_probability: number;
  counterfactual_risk_band: string;
  probability_delta: number;
  direction_of_change: string;
  modified_features: Record<string, { original: unknown; modified: unknown }>;
  actionable_mode?: boolean;
}

export interface EMIResponse {
  principal: number;
  annual_interest_rate: number;
  tenure_months: number;
  monthly_emi: number;
  total_interest: number;
  total_payment: number;
  amortization_schedule: Array<{
    month: number;
    payment: number;
    principal_payment: number;
    interest_payment: number;
    remaining_balance: number;
  }>;
}

export interface StressTestResponse {
  baseline_income: number;
  baseline_essential_expenses: number;
  baseline_discretionary_expenses: number;
  baseline_existing_emis: number;
  proposed_emi: number;
  liquid_savings: number;
  baseline_surplus: number;
  baseline_emi_to_income_ratio: number | null;
  baseline_runway_months: number | null;
  stressed_income: number;
  stressed_essential_expenses: number;
  stressed_discretionary_expenses: number;
  stressed_existing_emis: number;
  stressed_proposed_emi: number;
  stressed_surplus: number;
  stressed_emi_to_income_ratio: number | null;
  stressed_runway_months: number | null;
  surplus_change: number;
  runway_change_months: number | null;
  is_insolvent: boolean;
  risk_assessment: string;
}

export interface PortfolioRiskMetrics {
  portfolio_name: string;
  currency: string;
  symbols: string[];
  weights: number[];
  portfolio_value?: number | null;
  position_values?: Record<string, number> | null;
  data_source_mode?: string;
  observations_count: number;
  start_date: string;
  end_date: string;
  annualized_volatility: number;
  historical_var_95: number;
  historical_var_99: number;
  parametric_var_95: number;
  parametric_var_99: number;
  expected_shortfall_95: number;
  expected_shortfall_99: number;
  historical_var_95_amount?: number | null;
  historical_var_99_amount?: number | null;
  parametric_var_95_amount?: number | null;
  parametric_var_99_amount?: number | null;
  expected_shortfall_95_amount?: number | null;
  expected_shortfall_99_amount?: number | null;
  maximum_drawdown: number;
  mean_daily_return: number;
  asset_correlations: Record<string, Record<string, number>>;
  loss_convention?: string;
  assumptions?: Record<string, unknown>;
  selected_var_method?: string;
  horizon_days?: number;
  selected_var_95?: number | null;
  selected_var_99?: number | null;
  selected_es_95?: number | null;
  selected_es_99?: number | null;
  sharpe_ratio?: number | null;
  sortino_ratio?: number | null;
  drawdown_table?: Array<{
    peak_date: string;
    trough_date: string;
    recovery_date?: string | null;
    depth: number;
    duration_days: number;
    recovery_days?: number | null;
  }>;
  component_var_pct?: Record<string, number> | null;
  marginal_var?: Record<string, number> | null;
  benchmark_symbol?: string | null;
  benchmark_volatility?: number | null;
  beta_to_benchmark?: number | null;
  correlation_to_benchmark?: number | null;
  chart_series?: ChartSeries | null;
  fx_converted?: boolean;
  fx?: FxInfo | null;
}

export type FxMode = "strict" | "convert_to_base";

/** How currencies were handled. The conversion fields are present only when fx_converted is true. */
export interface FxInfo {
  mode: FxMode;
  base_currency: string;
  fx_converted: boolean;
  fx_pair?: string;
  fx_data_source?: string;
  converted_symbols?: string[];
  conversion_directions?: Record<string, string>;
  series_start?: string;
  series_end?: string;
  observations?: number;
  rate_start?: number;
  rate_end?: number;
  note?: string;
}

export interface ChartSeries {
  dates: string[];
  portfolio_cumulative_pct: number[];
  benchmark_cumulative_pct: (number | null)[] | null;
  drawdown_pct: number[];
  histogram: { lo: number; hi: number; count: number }[];
}

export interface ReplayContribution {
  symbol: string;
  weight: number;
  covered_weight_share: number;
  start_date: string;
  end_date: string;
  start_price: number;
  end_price: number;
  return: number;
  trough_return: number;
  contribution: number;
}

export interface StressReplayScenario {
  id: string;
  name: string;
  description: string;
  window_start: string;
  window_end: string;
  status: "ok" | "unavailable";
  currency: string;
  data_source: string;
  covered_weight: number;
  skipped: { symbol: string; reason: string }[];
  contributions: ReplayContribution[];
  portfolio_return: number | null;
  portfolio_loss_pct: number | null;
  portfolio_loss_amount: number | null;
  fx?: Record<string, unknown> | null;
}

export interface ReverseStressContribution {
  symbol: string;
  weight: number;
  beta: number;
  shock: number;
  contribution: number;
}

export interface ReverseStressResult {
  currency: string;
  target_loss_pct: number;
  target_loss_amount: number | null;
  uniform_asset_shock: number;
  uniform_contributions: ReverseStressContribution[];
  benchmark_symbol: string;
  lookback_observations: number;
  lookback_start: string;
  lookback_end: string;
  portfolio_beta: number;
  implied_benchmark_shock: number | null;
  beta_contributions: ReverseStressContribution[];
  note: string | null;
  fx?: FxInfo | null;
}

export interface StressInput {
  holdings: Array<{ symbol: string; weight?: number; position_value?: number }>;
  currency: string;
  fx_mode: FxMode;
  portfolio_value?: number;
}

export interface StressScenarioResult {
  scenario_name: string;
  portfolio_loss_pct: number;
  individual_asset_losses: Record<string, number>;
  assumptions: Record<string, unknown>;
}

export interface VaRValidationResponse {
  portfolio_name: string;
  currency: string;
  method: string;
  confidence_level: number;
  lookback_window: number;
  n_obs: number;
  window: number;
  confidence: number;
  exceptions: number;
  expected_exceptions: number;
  forecast_count: number;
  exception_count: number;
  exception_rate: number;
  expected_exception_rate: number;
  basel_zone: string;
  basel_zone_cumulative_prob: number;
  basel_capital_multiplier?: number | null;
  kupiec_lr_stat: number | null;
  kupiec_p_value: number | null;
  kupiec_test_passed: boolean;
  christoffersen_lr_stat?: number | null;
  christoffersen_p_value?: number | null;
  christoffersen_test_passed?: boolean | null;
  christoffersen_cc_stat?: number | null;
  christoffersen_cc_p_value?: number | null;
  christoffersen_cc_test_passed?: boolean | null;
  summary_message: string;
  validation_points: Array<{
    date: string;
    realized_loss: number;
    forecast_var: number;
    is_exception: boolean;
  }>;
  fx?: FxInfo | null;
}

export interface VaRModelComparisonItem {
  method: string;
  exceptions: number;
  expected_exceptions: number;
  exception_rate: number;
  expected_exception_rate: number;
  basel_zone: string;
  basel_capital_multiplier: number;
  kupiec_p_value: number | null;
  kupiec_test_passed: boolean;
  christoffersen_ind_p_value: number | null;
  christoffersen_ind_passed: boolean | null;
  christoffersen_cc_p_value: number | null;
  christoffersen_cc_test_passed: boolean | null;
  score: number;
}

export interface VaRCompareResponse {
  portfolio_name: string;
  currency: string;
  confidence_level: number;
  lookback_window: number;
  forecast_count: number;
  models: VaRModelComparisonItem[];
  recommended_method: string;
  recommendation_reason: string;
  fx?: FxInfo | null;
}

export interface StockSearchResult {
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  is_cached: boolean;
  status: "verified" | "known" | "valid_remote";
  alias_of?: string | null;
  note?: string | null;
}

export interface StockSearchResponse {
  query: string;
  results: StockSearchResult[];
}

export interface SymbolValidateResponse {
  symbol: string;
  canonical_symbol: string;
  name: string;
  exchange: string;
  currency: string;
  state: "verified_snapshot" | "live_validated" | "not_available";
  is_cached: boolean;
  observations_count?: number | null;
  start_date?: string | null;
  end_date?: string | null;
  alias_note?: string | null;
  error_reason?: string | null;
  message: string;
}

export interface VaRValidationHistoryItem {
  id: string;
  created_at: string;
  portfolio_name: string;
  currency: string;
  symbols: string[];
  method: string;
  confidence_level: number;
  lookback: number;
  forecast_count: number;
  exception_count: number;
  exception_rate: number;
  expected_exception_rate: number;
  basel_zone?: string | null;
  kupiec_p_value?: number | null;
  kupiec_test_passed?: boolean | null;
  christoffersen_p_value?: number | null;
  christoffersen_test_passed?: boolean | null;
}

export interface CopilotResponse {
  answer: string;
  intent: string;
  tool_trace: Array<{
    tool_name: string;
    arguments: Record<string, unknown>;
    output: Record<string, unknown>;
    is_authoritative: boolean;
  }>;
  citations: Array<{
    title: string;
    publisher: string;
    snippet: string;
    url: string;
  }>;
  offline_fallback_mode: boolean;
  safety_disclaimer: string;
}

export interface ModelRegistryItem {
  id: string;
  model_name: string;
  version: string;
  dataset_id: string;
  status: string;
  trained_at: string;
  checksum: string;
  metrics: Record<string, number | string | number[][]>;
}

export interface DriftRunResponse {
  id: string;
  model_version_id: string;
  reference_batch_id: string;
  current_batch_id: string;
  overall_psi: number;
  overall_status: string;
  features: Array<{
    feature_name: string;
    psi_value: number;
    drift_status: string;
    reference_count: number;
    current_count: number;
  }>;
  run_timestamp: string;
}

export interface MethodologyResponse {
  version: string;
  credit_risk: Record<string, unknown>;
  financial_stress: Record<string, unknown>;
  market_risk: Record<string, unknown>;
  var_validation: Record<string, unknown>;
  disclaimers: string[];
  known_limitations: string[];
}

// ─── API Methods ──────────────────────────────────────────────────────────────

export const api = {
  health: () => apiFetch<HealthResponse>("/health"),
  
  system: {
    status: () => apiFetch<SystemStatus>("/api/v1/system/status"),
  },

  credit: {
    models: () => apiFetch<CreditModelMetadata[]>("/api/v1/credit/models"),
    samples: () => apiFetch<BorrowerProfileSample[]>("/api/v1/credit/samples"),
    score: (features: Record<string, unknown>) =>
      apiFetch<CreditScoreResponse>("/api/v1/credit/score", {
        method: "POST",
        body: JSON.stringify({ features }),
      }),
    explain: (features: Record<string, unknown>, top_n = 8) =>
      apiFetch<CreditExplainResponse>("/api/v1/credit/explain", {
        method: "POST",
        body: JSON.stringify({ features, top_n }),
      }),
    whatIf: (baseline_features: Record<string, unknown>, modifications: Record<string, unknown>) =>
      apiFetch<WhatIfResponse>("/api/v1/credit/what-if", {
        method: "POST",
        body: JSON.stringify({ baseline_features, modifications }),
      }),
  },

  finance: {
    emi: (params: { principal: number; annual_interest_rate: number; tenure_months: number; include_schedule?: boolean }) =>
      apiFetch<EMIResponse>("/api/v1/finance/emi", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    stressTest: (params: Record<string, unknown>) =>
      apiFetch<StressTestResponse>("/api/v1/finance/stress-test", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  },

  market: {
    universe: () =>
      apiFetch<{
        supported_symbols: string[];
        symbol_currencies?: Record<string, string>;
        supported_currencies?: string[];
        provider: string;
        currency: string;
        frequency: string;
        manifest_present: boolean;
      }>("/api/v1/market/universe"),
    search: (
      query: string,
      limit = 15,
      currency?: string,
      options?: { sector?: string; index?: string; cap_bucket?: string; page?: number }
    ) => {
      let url = `/api/v1/market/search?q=${encodeURIComponent(query)}&limit=${limit}`;
      if (currency) url += `&currency=${encodeURIComponent(currency)}`;
      if (options?.sector) url += `&sector=${encodeURIComponent(options.sector)}`;
      if (options?.index) url += `&index=${encodeURIComponent(options.index)}`;
      if (options?.cap_bucket) url += `&cap_bucket=${encodeURIComponent(options.cap_bucket)}`;
      if (options?.page) url += `&page=${options.page}`;
      return apiFetch<StockSearchResponse>(url);
    },
    validateSymbol: (symbol: string, target_currency?: string) =>
      apiFetch<SymbolValidateResponse>("/api/v1/market/validate-symbol", {
        method: "POST",
        body: JSON.stringify({ symbol, target_currency }),
      }),
    analyze: (params: {
      holdings: Array<{ symbol: string; weight?: number; position_value?: number }>;
      portfolio_name?: string;
      currency?: string;
      lookback_days?: number;
      return_method?: string;
      portfolio_value?: number;
      var_method?: string;
      horizon_days?: number;
      benchmark_symbol?: string;
      fx_mode?: FxMode;
    }) =>
      apiFetch<PortfolioRiskMetrics>("/api/v1/market/portfolio/analyze", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    stressTest: (
      holdings: Array<{ symbol: string; weight?: number; position_value?: number }>,
      custom_scenarios?: Array<{ name: string; description: string; shocks: Record<string, number> }>,
      fx?: { currency: string; fx_mode: FxMode }
    ) =>
      apiFetch<StressScenarioResult[]>("/api/v1/market/portfolio/stress-test", {
        method: "POST",
        body: JSON.stringify({ holdings, custom_scenarios, ...fx }),
      }),
    stressReplay: (input: StressInput, scenarios?: string[]) =>
      apiFetch<StressReplayScenario[]>("/api/v1/market/portfolio/stress/replay", {
        method: "POST",
        body: JSON.stringify({ ...input, scenarios }),
      }),
    stressReverse: (input: StressInput, target: { target_loss_pct?: number; target_loss_amount?: number }) =>
      apiFetch<ReverseStressResult>("/api/v1/market/portfolio/stress/reverse", {
        method: "POST",
        body: JSON.stringify({ ...input, ...target }),
      }),
    validateVar: (params: {
      holdings: Array<{ symbol: string; weight?: number; position_value?: number }>;
      portfolio_name?: string;
      currency?: string;
      method?: string;
      confidence_level?: number;
      lookback_window?: number;
      fx_mode?: FxMode;
    }) =>
      apiFetch<VaRValidationResponse>("/api/v1/market/var/validate", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    compareVar: (params: {
      holdings: Array<{ symbol: string; weight?: number; position_value?: number }>;
      portfolio_name?: string;
      currency?: string;
      confidence_level?: number;
      lookback_window?: number;
      methods?: string[];
      fx_mode?: FxMode;
    }) =>
      apiFetch<VaRCompareResponse>("/api/v1/market/var/compare", {
        method: "POST",
        body: JSON.stringify(params),
      }),
    history: (limit = 20) =>
      apiFetch<VaRValidationHistoryItem[]>(`/api/v1/market/var/history?limit=${limit}`),
    refresh: (params?: { fetch_live?: boolean; symbols?: string[] }) =>
      apiFetch<{
        status: string;
        data_source_mode: string;
        live_error?: string | null;
        provider: string;
        currency: string;
        supported_symbols: string[];
        snapshot_details: Record<string, unknown>;
        manifest_present: boolean;
        refreshed_at: string;
      }>("/api/v1/market/refresh", {
        method: "POST",
        body: JSON.stringify(params || {}),
      }),
  },

  copilot: {
    message: (message: string) =>
      apiFetch<CopilotResponse>("/api/v1/copilot/message", {
        method: "POST",
        body: JSON.stringify({ message }),
      }),
  },

  monitoring: {
    models: () => apiFetch<ModelRegistryItem[]>("/api/v1/monitoring/models"),
    runDrift: (params?: { reference_batch_id?: string; current_batch_id?: string }) =>
      apiFetch<DriftRunResponse>("/api/v1/monitoring/drift/run", {
        method: "POST",
        body: JSON.stringify(params || { reference_batch_id: "training_baseline", current_batch_id: "current_batch" }),
      }),
  },

  methodology: {
    get: () => apiFetch<MethodologyResponse>("/api/v1/methodology"),
  },
};
