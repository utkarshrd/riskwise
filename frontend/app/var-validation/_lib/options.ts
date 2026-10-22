import type { PresetMap } from "@/lib/portfolio";

export const DEFAULT_PRESET = "us_tech";

// Validation uses weights only, so defaultVal is just a placeholder required by the shared builder.
export const PRESET_PORTFOLIOS: PresetMap = {
  us_tech: {
    name: "US Tech & Benchmark (USD)",
    currency: "USD",
    defaultVal: 100000,
    holdings: [
      { symbol: "SPY", name: "SPDR S&P 500 ETF", exchange: "NYSE Arca", currency: "USD", weight: 0.7 },
      { symbol: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", currency: "USD", weight: 0.3 },
    ],
  },
  us_largecap: {
    name: "US Large-Cap Growth (USD)",
    currency: "USD",
    defaultVal: 100000,
    holdings: [
      { symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", currency: "USD", weight: 0.5 },
      { symbol: "GOOGL", name: "Alphabet Inc.", exchange: "NASDAQ", currency: "USD", weight: 0.5 },
    ],
  },
  india_core: {
    name: "India Leaders (INR)",
    currency: "INR",
    defaultVal: 100000,
    holdings: [
      { symbol: "RELIANCE.NS", name: "Reliance Industries", exchange: "NSE", currency: "INR", weight: 0.5 },
      { symbol: "TCS.NS", name: "Tata Consultancy Services", exchange: "NSE", currency: "INR", weight: 0.5 },
    ],
  },
  nse_bench: {
    name: "NSE Index Equities (INR)",
    currency: "INR",
    defaultVal: 100000,
    holdings: [
      { symbol: "NIFTYBEES.NS", name: "Nifty BeES ETF", exchange: "NSE", currency: "INR", weight: 0.6 },
      { symbol: "HDFCBANK.NS", name: "HDFC Bank Limited", exchange: "NSE", currency: "INR", weight: 0.4 },
    ],
  },
};

export const WINDOW_OPTIONS = [
  { value: 60, label: "60 Days (Short-term calibration)" },
  { value: 100, label: "100 Days (Standard rolling window)" },
  { value: 250, label: "250 Days (1 Year, Basel standard)" },
];
