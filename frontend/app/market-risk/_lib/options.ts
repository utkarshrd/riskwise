import type { PresetMap } from "@/lib/portfolio";
import type { MetricKey } from "@/lib/metric-docs";

export const VAR_METHODS: { value: string; label: string; metric: MetricKey }[] = [
  { value: "historical", label: "Historical Quantile (Empirical)", metric: "historical_var" },
  { value: "gaussian", label: "Gaussian Parametric (Normal)", metric: "parametric_var" },
  { value: "student_t", label: "Student-t (Fat Tails)", metric: "student_t_var" },
  { value: "cornish_fisher", label: "Cornish-Fisher (Skew/Kurtosis)", metric: "cornish_fisher_var" },
  { value: "ewma", label: "EWMA (RiskMetrics λ=0.94)", metric: "ewma_var" },
  { value: "monte_carlo", label: "Monte Carlo (Cholesky Seeded)", metric: "monte_carlo_var" },
  { value: "garch", label: "GARCH(1,1) Volatility", metric: "garch_var" },
  { value: "fhs", label: "Filtered Historical Simulation", metric: "fhs_var" },
];

export const DEFAULT_PRESET = "us_tech";

export const PRESET_PORTFOLIOS: PresetMap = {
  us_tech: {
    name: "US Tech & Benchmark (USD)",
    currency: "USD",
    defaultVal: 100000,
    holdings: [
      { symbol: "SPY", name: "SPDR S&P 500 ETF", exchange: "NYSE Arca", currency: "USD", weight: 0.4 },
      { symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", currency: "USD", weight: 0.3 },
      { symbol: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", currency: "USD", weight: 0.3 },
    ],
  },
  us_mag: {
    name: "US Large-Cap Tech (USD)",
    currency: "USD",
    defaultVal: 250000,
    holdings: [
      { symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", currency: "USD", weight: 0.34 },
      { symbol: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", currency: "USD", weight: 0.33 },
      { symbol: "GOOGL", name: "Alphabet Inc.", exchange: "NASDAQ", currency: "USD", weight: 0.33 },
    ],
  },
  india_bluechip: {
    name: "India Blue-Chip Leaders (INR)",
    currency: "INR",
    defaultVal: 1000000,
    holdings: [
      { symbol: "RELIANCE.NS", name: "Reliance Industries", exchange: "NSE", currency: "INR", weight: 0.35 },
      { symbol: "TCS.NS", name: "Tata Consultancy Services", exchange: "NSE", currency: "INR", weight: 0.35 },
      { symbol: "HDFCBANK.NS", name: "HDFC Bank Limited", exchange: "NSE", currency: "INR", weight: 0.3 },
    ],
  },
  nse_benchmark: {
    name: "NSE Index & Core Equities (INR)",
    currency: "INR",
    defaultVal: 1500000,
    holdings: [
      { symbol: "NIFTYBEES.NS", name: "Nifty BeES ETF", exchange: "NSE", currency: "INR", weight: 0.4 },
      { symbol: "INFY.NS", name: "Infosys Limited", exchange: "NSE", currency: "INR", weight: 0.3 },
      { symbol: "ICICIBANK.NS", name: "ICICI Bank Limited", exchange: "NSE", currency: "INR", weight: 0.3 },
    ],
  },
};
