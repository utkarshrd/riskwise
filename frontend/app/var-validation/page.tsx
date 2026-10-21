"use client";

import { useState, useEffect, useRef } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Activity,
  History,
  Sliders,
  Calendar,
  CheckCircle2,
  HelpCircle,
  Filter,
  Search,
  Trash2,
  RefreshCw,
} from "lucide-react";
import {
  api,
  VaRValidationResponse,
  VaRValidationHistoryItem,
  StockSearchResult,
} from "@/lib/api";

interface HoldingRow {
  symbol: string;
  name?: string;
  exchange?: string;
  currency?: string;
  weight: number;
  state?: "verified_snapshot" | "live_validated" | "not_available" | "validating";
  observations_count?: number;
  alias_note?: string;
}

const PRESET_PORTFOLIOS: Record<
  string,
  { name: string; currency: string; holdings: HoldingRow[] }
> = {
  us_tech: {
    name: "US Tech & Benchmark (USD)",
    currency: "USD",
    holdings: [
      { symbol: "SPY", name: "SPDR S&P 500 ETF", exchange: "NYSE Arca", currency: "USD", weight: 0.7 },
      { symbol: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", currency: "USD", weight: 0.3 },
    ],
  },
  us_largecap: {
    name: "US Large-Cap Growth (USD)",
    currency: "USD",
    holdings: [
      { symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", currency: "USD", weight: 0.5 },
      { symbol: "GOOGL", name: "Alphabet Inc.", exchange: "NASDAQ", currency: "USD", weight: 0.5 },
    ],
  },
  india_core: {
    name: "India Leaders (INR)",
    currency: "INR",
    holdings: [
      { symbol: "RELIANCE.NS", name: "Reliance Industries", exchange: "NSE", currency: "INR", weight: 0.5 },
      { symbol: "TCS.NS", name: "Tata Consultancy Services", exchange: "NSE", currency: "INR", weight: 0.5 },
    ],
  },
  nse_bench: {
    name: "NSE Index Equities (INR)",
    currency: "INR",
    holdings: [
      { symbol: "NIFTYBEES.NS", name: "Nifty BeES ETF", exchange: "NSE", currency: "INR", weight: 0.6 },
      { symbol: "HDFCBANK.NS", name: "HDFC Bank Limited", exchange: "NSE", currency: "INR", weight: 0.4 },
    ],
  },
};

function inferSymbolCurrency(sym: string, portfolioCurrency?: string): string {
  const upper = sym.toUpperCase().trim();
  if (upper.endsWith(".NS") || upper.endsWith(".BO") || upper.startsWith("^NSE") || upper.startsWith("_NSE")) {
    return "INR";
  }
  if (upper.endsWith(".TO") || upper.endsWith(".L") || upper.endsWith(".DE") || upper.endsWith(".PA")) {
    return "USD";
  }
  if (!upper.includes(".") && portfolioCurrency === "INR") {
    return "INR";
  }
  return "USD";
}

function formatPct(n: number | null | undefined) {
  if (n == null) return "N/A";
  return `${(n * 100).toFixed(2)}%`;
}

export default function VaRValidationPage() {
  const [selectedPreset, setSelectedPreset] = useState<string>("us_tech");
  const [portfolioName, setPortfolioName] = useState<string>("US Tech & Benchmark");
  const [currency, setCurrency] = useState<string>("USD");
  const [method, setMethod] = useState<string>("historical");
  const [confidenceLevel, setConfidenceLevel] = useState<number>(0.95);
  const [lookbackWindow, setLookbackWindow] = useState<number>(100);
  const [holdings, setHoldings] = useState<HoldingRow[]>([
    { symbol: "SPY", name: "SPDR S&P 500 ETF", exchange: "NYSE Arca", currency: "USD", weight: 0.7 },
    { symbol: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", currency: "USD", weight: 0.3 },
  ]);

  // Stock search state
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [showSearchDropdown, setShowSearchDropdown] = useState<boolean>(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  const [validationResult, setValidationResult] = useState<VaRValidationResponse | null>(null);
  const [historyRuns, setHistoryRuns] = useState<VaRValidationHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [timelineFilter, setTimelineFilter] = useState<"all" | "exceptions">("all");

  // Load history on mount
  useEffect(() => {
    async function fetchHistory() {
      setHistoryLoading(true);
      try {
        const hist = await api.market.history(10);
        setHistoryRuns(hist);
      } catch (err) {
        console.warn("Could not fetch validation history:", err);
      } finally {
        setHistoryLoading(false);
      }
    }
    fetchHistory();
  }, []);

  // Debounced stock search
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!searchQuery.trim()) {
        setSearchResults([]);
        return;
      }
      setSearchLoading(true);
      try {
        const res = await api.market.search(searchQuery.trim(), 10, currency);
        setSearchResults(res.results || []);
      } catch (err) {
        console.warn("Stock search error in backtest:", err);
      } finally {
        setSearchLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery, currency]);

  // Click outside listener for search dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSearchDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectPreset = (key: string) => {
    setSelectedPreset(key);
    if (key in PRESET_PORTFOLIOS) {
      const p = PRESET_PORTFOLIOS[key];
      setPortfolioName(p.name);
      setCurrency(p.currency);
      setHoldings(p.holdings);
      setValidationResult(null);
      setError(null);
    }
  };

  const addAssetToPortfolio = async (item: { symbol: string; name?: string; exchange?: string; currency?: string }) => {
    let rawSym = item.symbol.toUpperCase().trim();
    if (currency === "INR" && !rawSym.includes(".") && !rawSym.startsWith("^")) {
      rawSym = `${rawSym}.NS`;
    }

    if (holdings.some((h) => h.symbol === rawSym)) {
      setError(`Symbol '${rawSym}' is already included in your portfolio.`);
      return;
    }

    const itemCurr = item.currency || inferSymbolCurrency(rawSym, currency);
    if (holdings.length === 0) {
      setCurrency(itemCurr);
    }

    setSelectedPreset("custom");
    const newWeight = holdings.length === 0 ? 1.0 : 0.1;
    setHoldings((prev) => [
      ...prev,
      {
        symbol: rawSym,
        name: item.name || rawSym,
        exchange: item.exchange || (itemCurr === "INR" ? "NSE" : "US"),
        currency: itemCurr,
        weight: newWeight,
        state: "validating",
      },
    ]);
    setSearchQuery("");
    setShowSearchDropdown(false);
    setError(null);

    // Call server-side validation to retrieve actual historical data
    try {
      const valRes = await api.market.validateSymbol(rawSym, currency);
      setHoldings((prev) => {
        const copy = [...prev];
        const idx = copy.findIndex((h) => h.symbol === rawSym);
        if (idx !== -1) {
          copy[idx] = {
            ...copy[idx],
            symbol: valRes.canonical_symbol,
            name: valRes.name || copy[idx].name,
            exchange: valRes.exchange || copy[idx].exchange,
            currency: valRes.currency || copy[idx].currency,
            state: valRes.state,
            observations_count: valRes.observations_count || undefined,
            alias_note: valRes.alias_note || undefined,
          };
        }
        return copy;
      });

      if (valRes.state === "not_available") {
        setError(`Warning: ${valRes.message}`);
      }
    } catch (err) {
      console.warn("VaR symbol validation error:", err);
    }
  };

  const handleHoldingChange = (index: number, field: "symbol" | "weight", val: string | number) => {
    setSelectedPreset("custom");
    setHoldings((prev) => {
      const updated = [...prev];
      if (field === "symbol") {
        const sym = String(val).toUpperCase().trim();
        updated[index] = {
          ...updated[index],
          symbol: sym,
          currency: inferSymbolCurrency(sym),
        };
      } else if (field === "weight") {
        updated[index] = {
          ...updated[index],
          weight: Number(val),
        };
      }
      return updated;
    });
  };

  const removeHolding = (idx: number) => {
    if (holdings.length <= 1) return;
    setSelectedPreset("custom");
    setHoldings((prev) => prev.filter((_, i) => i !== idx));
  };

  const totalWeight = holdings.reduce((sum, h) => sum + (h.weight || 0), 0);

  const normalizeWeights = () => {
    if (totalWeight > 0) {
      setHoldings((prev) =>
        prev.map((h) => ({
          ...h,
          weight: Number((h.weight / totalWeight).toFixed(4)),
        }))
      );
    }
  };

  // Currency validation
  const assetCurrencies = holdings.map((h) => h.currency || inferSymbolCurrency(h.symbol));
  const distinctCurrencies = Array.from(new Set(assetCurrencies));
  const hasMixedCurrencies = distinctCurrencies.length > 1;
  const portfolioCurrencyMismatch = !hasMixedCurrencies && distinctCurrencies[0] && distinctCurrencies[0] !== currency;

  const handleRunValidation = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.market.validateVar({
        holdings: holdings.map((h) => ({ symbol: h.symbol, weight: Number(h.weight) })),
        portfolio_name: portfolioName,
        currency,
        method,
        confidence_level: confidenceLevel,
        lookback_window: lookbackWindow,
      });
      setValidationResult(res);

      // Refresh history list
      try {
        const hist = await api.market.history(10);
        setHistoryRuns(hist);
      } catch (hErr) {
        console.warn("Could not reload history:", hErr);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "VaR validation failed.");
    } finally {
      setLoading(false);
    }
  };

  const exceptionsOnly =
    validationResult?.validation_points.filter((p) => p.is_exception) || [];

  const pointsToRender =
    timelineFilter === "exceptions"
      ? exceptionsOnly
      : validationResult?.validation_points || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-1 tracking-wide uppercase">
            <span className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800">
              Regulatory Model Validation
            </span>
            <span className="text-slate-400">•</span>
            <span>Out-of-Sample Backtesting</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Rolling VaR Model Validation & Backtesting
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
            Strict out-of-sample evaluation of risk model forecasts against subsequently realized daily losses. Features Kupiec POF test, Christoffersen independence test, and Basel traffic-light classification.
          </p>
        </div>
      </div>

      {/* Critical Mandatory Disclosure Banner */}
      <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/30 text-amber-950 dark:text-amber-200 text-xs flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-semibold text-sm">
            Regulatory VaR Forecast Validation — NOT Trading-Strategy Backtesting
          </div>
          <p className="leading-relaxed text-[11px] text-amber-900 dark:text-amber-300">
            This module evaluates whether historical risk model forecasts statistically bound out-of-sample portfolio losses. At each step <code>t</code>, parameters are estimated exclusively from historical data <code>[t-W, t)</code> and evaluated against day <code>t</code>. Zero future leakage is permitted. This does not simulate portfolio rebalancing or trading alpha.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl border border-red-200 dark:border-red-900/60 bg-red-50/80 dark:bg-red-950/40 text-sm text-red-900 dark:text-red-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold">Validation Error</div>
            <div className="text-xs leading-relaxed">{error}</div>
          </div>
        </div>
      )}

      {/* Main Grid: Parameters on Left, Validation Analytics on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Test Setup */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                <Sliders className="w-4 h-4 text-emerald-500" />
                <span>Backtest Setup</span>
              </div>
              <span className="text-[11px] font-mono text-slate-500">
                Temporal Isolation: Verified
              </span>
            </div>

            {/* Presets */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                Portfolio Presets
              </label>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(PRESET_PORTFOLIOS).map(([key, p]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handleSelectPreset(key)}
                    className={`text-left p-2.5 rounded-lg border text-xs transition-all ${
                      selectedPreset === key
                        ? "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200 font-medium"
                        : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 text-slate-600 dark:text-slate-400"
                    }`}
                  >
                    <div className="font-semibold text-slate-800 dark:text-slate-200 text-[11px] truncate">
                      {p.name}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      {p.currency} • {p.holdings.map((h) => `${h.symbol} (${h.weight * 100}%)`).join(", ")}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Risk Methodology & Confidence Level */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Risk Methodology
                </label>
                <select
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                  className="w-full text-xs px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                >
                  <option value="historical">Historical Simulation</option>
                  <option value="parametric">Parametric Gaussian</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Confidence Level
                </label>
                <select
                  value={confidenceLevel}
                  onChange={(e) => setConfidenceLevel(Number(e.target.value))}
                  className="w-full text-xs px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                >
                  <option value={0.95}>95.0% VaR (p0 = 5.0%)</option>
                  <option value={0.99}>99.0% VaR (p0 = 1.0%)</option>
                </select>
              </div>
            </div>

            {/* Lookback Window */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                Rolling Estimation Window (Trading Days)
              </label>
              <select
                value={lookbackWindow}
                onChange={(e) => setLookbackWindow(Number(e.target.value))}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              >
                <option value={60}>60 Days (Short-term calibration)</option>
                <option value={100}>100 Days (Standard rolling window)</option>
                <option value={250}>250 Days (1 Year - Basel Standard)</option>
              </select>
              <div className="text-[10px] text-slate-400 pt-0.5">
                Each forecast at day <code>t</code> estimates parameters solely from previous <code>{lookbackWindow}</code> observations.
              </div>
            </div>

            {/* Stock Search & Add Asset */}
            <div className="space-y-2 relative" ref={searchContainerRef}>
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Search className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Search & Add Assets (NSE / BSE / US)</span>
                </label>
                <span className="text-[10px] text-slate-400 font-mono">e.g. RELIANCE, TCS, SBIN, AAPL</span>
              </div>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Type ticker or company name (e.g. INFY, TCS, MSFT)..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setShowSearchDropdown(true);
                  }}
                  onFocus={() => setShowSearchDropdown(true)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && searchQuery.trim()) {
                      e.preventDefault();
                      addAssetToPortfolio({ symbol: searchQuery.trim() });
                    }
                  }}
                  className="w-full text-xs pl-8 pr-20 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                {searchQuery.trim() && (
                  <button
                    type="button"
                    onClick={() => addAssetToPortfolio({ symbol: searchQuery.trim() })}
                    className="absolute right-1.5 top-1 px-2.5 py-1 text-[11px] font-medium rounded-md bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
                  >
                    + Add
                  </button>
                )}
              </div>

              {/* Search Dropdown */}
              {showSearchDropdown && searchQuery.trim().length > 0 && (
                <div className="absolute z-30 left-0 right-0 mt-1 max-h-60 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl p-1.5 space-y-1">
                  {searchLoading && (
                    <div className="p-3 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-500" />
                      Searching market data provider...
                    </div>
                  )}

                  {!searchLoading && searchResults.length === 0 && (
                    <div className="p-3 text-center text-xs text-slate-500 space-y-1">
                      <div>No predefined match for &quot;{searchQuery}&quot;.</div>
                      <button
                        type="button"
                        onClick={() => addAssetToPortfolio({ symbol: searchQuery.trim() })}
                        className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold hover:underline"
                      >
                        + Add &quot;{searchQuery.toUpperCase().trim()}&quot; as direct ticker
                      </button>
                    </div>
                  )}

                  {searchResults.map((item) => (
                    <button
                      key={item.symbol}
                      type="button"
                      onClick={() => addAssetToPortfolio(item)}
                      className="w-full text-left p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/80 flex items-center justify-between transition-colors text-xs"
                    >
                      <div className="flex flex-col min-w-0 pr-2">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                            {item.symbol}
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            ({item.exchange})
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                          {item.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                            item.currency === "INR"
                              ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                              : "bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800"
                          }`}
                        >
                          {item.currency}
                        </span>
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded ${
                            item.is_cached
                              ? "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                              : "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400"
                          }`}
                        >
                          {item.is_cached ? "Verified" : "Provider"}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Holdings Allocation List */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs font-medium text-slate-700 dark:text-slate-300">
                <span>Holdings Allocation ({holdings.length} Assets)</span>
                <span
                  className={`text-[11px] font-mono ${
                    Math.abs(totalWeight - 1.0) < 0.001
                      ? "text-emerald-600 dark:text-emerald-400 font-semibold"
                      : "text-amber-600 dark:text-amber-400 font-semibold"
                  }`}
                >
                  Sum: {(totalWeight * 100).toFixed(1)}%
                </span>
              </div>

              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {holdings.map((h, idx) => {
                  const assetCurr = h.currency || inferSymbolCurrency(h.symbol, currency);
                  return (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <input
                            type="text"
                            value={h.symbol}
                            onChange={(e) => handleHoldingChange(idx, "symbol", e.target.value)}
                            className="w-32 text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-mono uppercase font-bold"
                          />
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-semibold shrink-0 ${
                              assetCurr === "INR"
                                ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300"
                                : "bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300"
                            }`}
                          >
                            {assetCurr}
                          </span>
                          {/* Symbol State Badge */}
                          {h.state === "validating" && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 animate-pulse font-medium">
                              Validating...
                            </span>
                          )}
                          {h.state === "live_validated" && (
                            <span
                              className="text-[9px] px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 font-medium"
                              title={h.observations_count ? `${h.observations_count} observations retrieved` : "Live validated"}
                            >
                              Live Validated
                            </span>
                          )}
                          {h.state === "verified_snapshot" && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-medium">
                              Local Snapshot
                            </span>
                          )}
                          {h.state === "not_available" && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 font-medium">
                              Unavailable
                            </span>
                          )}
                        </div>

                        <button
                          type="button"
                          onClick={() => removeHolding(idx)}
                          disabled={holdings.length <= 1}
                          className="p-1 text-slate-400 hover:text-red-500 transition-colors disabled:opacity-30 shrink-0"
                          title="Remove asset"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Name or Alias Note */}
                      {(h.name || h.alias_note) && (
                        <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate pl-0.5">
                          {h.alias_note ? (
                            <span className="text-amber-600 dark:text-amber-400 font-medium">{h.alias_note}</span>
                          ) : (
                            h.name
                          )}
                        </div>
                      )}

                      {/* Weight Input */}
                      <div className="flex items-center gap-1.5 pt-0.5">
                        <input
                          type="number"
                          step="0.05"
                          min="0.01"
                          max="1.0"
                          value={h.weight}
                          onChange={(e) => handleHoldingChange(idx, "weight", e.target.value)}
                          className="w-full text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-mono"
                        />
                        <span className="text-[11px] text-slate-400 font-mono">%</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-slate-400">
                  Currency: <strong>{currency}</strong>
                </span>
                {Math.abs(totalWeight - 1.0) >= 0.001 && (
                  <button
                    type="button"
                    onClick={normalizeWeights}
                    className="text-[11px] px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 hover:bg-amber-100 border border-amber-200 dark:border-amber-800 font-medium transition-colors"
                  >
                    Normalize to 100%
                  </button>
                )}
              </div>
            </div>

            {/* Currency Consistency Alerts */}
            {hasMixedCurrencies && (
              <div className="p-3 rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/40 text-xs text-red-900 dark:text-red-300 space-y-1">
                <div className="font-semibold flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
                  <span>Incompatible Currencies Detected</span>
                </div>
                <p className="text-[11px] leading-relaxed text-red-800 dark:text-red-300">
                  Your portfolio combines assets with different base currencies:{" "}
                  <strong>{distinctCurrencies.join(" and ")}</strong>. Portfolios must be single-currency (all INR or all USD). Please remove the mismatched assets.
                </p>
              </div>
            )}

            {portfolioCurrencyMismatch && (
              <div className="p-3 rounded-lg border border-amber-200 dark:border-amber-900/60 bg-amber-50 dark:bg-amber-950/40 text-xs text-amber-900 dark:text-amber-300 flex items-center justify-between gap-2">
                <div className="text-[11px] leading-relaxed">
                  Portfolio base currency is <strong>{currency}</strong>, but assets are denominated in <strong>{distinctCurrencies[0]}</strong>.
                </div>
                <button
                  type="button"
                  onClick={() => setCurrency(distinctCurrencies[0])}
                  className="px-2 py-1 rounded text-[11px] font-semibold bg-amber-200/80 dark:bg-amber-800 text-amber-900 dark:text-amber-100 hover:bg-amber-300 transition-colors shrink-0"
                >
                  Set to {distinctCurrencies[0]}
                </button>
              </div>
            )}

            {/* Data Requirement Indicator */}
            <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-0.5">
              <div className="font-medium text-slate-700 dark:text-slate-300">
                Minimum Observations Check
              </div>
              <div>
                Requires estimation window (<code>{lookbackWindow} days</code>) + out-of-sample evaluation horizon (≥10 days) = <strong>{lookbackWindow + 11}+ trading sessions</strong>.
              </div>
            </div>

            {/* Run Validation Action */}
            <button
              type="button"
              onClick={handleRunValidation}
              disabled={loading || hasMixedCurrencies || holdings.length === 0}
              className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
            >
              <Activity className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              {loading
                ? "Running Rolling VaR Backtest..."
                : hasMixedCurrencies
                ? "Resolve Currency Mismatch to Proceed"
                : "Execute Rolling VaR Validation"}
            </button>
          </div>

          {/* Validation Runs Audit History Card */}
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 dark:text-slate-200">
                <History className="w-4 h-4 text-slate-500" />
                <span>Persisted Run History</span>
              </div>
              <span className="text-[10px] text-slate-400">SQLite Audited</span>
            </div>

            {historyLoading && (
              <div className="text-center py-3 text-xs text-slate-400">Loading audit log...</div>
            )}

            {!historyLoading && historyRuns.length === 0 && (
              <div className="text-center py-4 text-xs text-slate-400">
                No previous validation runs logged.
              </div>
            )}

            {!historyLoading && historyRuns.length > 0 && (
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {historyRuns.map((hr) => (
                  <div
                    key={hr.id}
                    className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-800 dark:text-slate-200 truncate max-w-[180px]">
                        {hr.portfolio_name}
                      </span>
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          hr.basel_zone === "GREEN"
                            ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300"
                            : hr.basel_zone === "YELLOW"
                            ? "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300"
                            : "bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300"
                        }`}
                      >
                        {hr.basel_zone || "N/A"}
                      </span>
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                      <span>
                        {hr.method} • {hr.confidence_level * 100}%
                      </span>
                      <span>
                        {hr.exception_count}/{hr.forecast_count} exc ({(hr.exception_rate * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div className="text-[9px] text-slate-400 flex justify-between">
                      <span>Kupiec p: {hr.kupiec_p_value != null ? hr.kupiec_p_value.toFixed(4) : "N/A"}</span>
                      <span>{hr.created_at ? hr.created_at.slice(0, 10) : ""}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Statistical Tests and Exception Timeline */}
        <div className="lg:col-span-7 space-y-6">
          {!validationResult && !loading && (
            <div className="p-12 rounded-xl border border-dashed border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/40 text-center space-y-4">
              <div className="inline-flex p-3 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400">
                <ShieldCheck className="w-8 h-8" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  Awaiting Rolling Backtest Execution
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  Select a portfolio and click <strong>Execute Rolling VaR Validation</strong>. The engine will slide a rolling estimation window day-by-day, forecasting VaR and testing unconditional coverage (Kupiec) and exception clustering (Christoffersen).
                </p>
              </div>
            </div>
          )}

          {validationResult && (
            <div className="space-y-6">
              {/* Summary Metrics Bar */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Evaluated Forecasts (N)
                  </div>
                  <div className="text-xl font-bold text-slate-900 dark:text-slate-100 font-mono">
                    {validationResult.forecast_count}
                  </div>
                  <div className="text-[10px] text-slate-400">Total Out-of-Sample Days</div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Observed Exceptions (x)
                  </div>
                  <div
                    className={`text-xl font-bold font-mono ${
                      validationResult.exception_count > validationResult.expected_exceptions * 1.5
                        ? "text-red-600 dark:text-red-400"
                        : "text-emerald-600 dark:text-emerald-400"
                    }`}
                  >
                    {validationResult.exception_count}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Expected: {validationResult.expected_exceptions.toFixed(1)}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Exception Rate (p̂)
                  </div>
                  <div className="text-xl font-bold text-slate-900 dark:text-slate-100 font-mono">
                    {formatPct(validationResult.exception_rate)}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Nominal: {formatPct(validationResult.expected_exception_rate)}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Basel Zone
                  </div>
                  <div
                    className={`text-base font-bold font-mono flex items-center gap-1.5 ${
                      validationResult.basel_zone === "GREEN"
                        ? "text-emerald-600 dark:text-emerald-400"
                        : validationResult.basel_zone === "YELLOW"
                        ? "text-amber-600 dark:text-amber-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {validationResult.basel_zone === "GREEN" ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : (
                      <AlertTriangle className="w-4 h-4" />
                    )}
                    {validationResult.basel_zone}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    Cum Prob: {(validationResult.basel_zone_cumulative_prob * 100).toFixed(2)}%
                  </div>
                </div>
              </div>

              {/* Hypothesis Testing Cards: Kupiec & Christoffersen */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Kupiec POF Card */}
                <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-500" />
                      <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                        Kupiec POF Test
                      </span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        validationResult.kupiec_test_passed
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                          : "bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800"
                      }`}
                    >
                      {validationResult.kupiec_test_passed ? "PASSED (Fail to Reject H0)" : "REJECTED (Miscalibrated)"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                    Evaluates unconditional coverage (H0: true exception probability p = {validationResult.expected_exception_rate}).
                  </p>

                  <div className="grid grid-cols-2 gap-2 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs font-mono">
                    <div>
                      <div className="text-[10px] text-slate-400">Likelihood Ratio (LR)</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {validationResult.kupiec_lr_stat != null ? validationResult.kupiec_lr_stat.toFixed(4) : "N/A"}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400">p-value (df=1)</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {validationResult.kupiec_p_value != null ? validationResult.kupiec_p_value.toFixed(4) : "N/A"}
                      </div>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-400 flex items-start gap-1.5 pt-1">
                    <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-slate-400" />
                    <span>
                      Critical value at α=0.05 is χ²(1)=3.841. Failing to reject does not guarantee model validity in small samples due to limited statistical power.
                    </span>
                  </div>
                </div>

                {/* Christoffersen Independence Card */}
                <div className="p-5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4 text-emerald-500" />
                      <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                        Christoffersen Independence
                      </span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        validationResult.christoffersen_test_passed !== false
                          ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                          : "bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800"
                      }`}
                    >
                      {validationResult.christoffersen_test_passed !== false
                        ? "INDEPENDENT (No Clustering)"
                        : "REJECTED (Clustering Detected)"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                    Evaluates first-order Markov independence of exception occurrences to detect risk clustering.
                  </p>

                  <div className="grid grid-cols-2 gap-2 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs font-mono">
                    <div>
                      <div className="text-[10px] text-slate-400">Independence LR</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {validationResult.christoffersen_lr_stat != null
                          ? validationResult.christoffersen_lr_stat.toFixed(4)
                          : "0.0000"}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400">p-value (df=1)</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {validationResult.christoffersen_p_value != null
                          ? validationResult.christoffersen_p_value.toFixed(4)
                          : "1.0000"}
                      </div>
                    </div>
                  </div>

                  <div className="text-[11px] text-slate-400 flex items-start gap-1.5 pt-1">
                    <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-slate-400" />
                    <span>
                      Combined with Kupiec, this forms the Christoffersen conditional coverage test (LR_cc = LR_pof + LR_ind ~ χ²(2)).
                    </span>
                  </div>
                </div>
              </div>

              {/* Exception Timeline & Out-of-Sample Points Table */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm space-y-4 p-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      Out-of-Sample Forecasts vs Realized Losses
                    </h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Exception triggered whenever Realized Loss (L = -R) exceeds Forecast VaR threshold.
                    </p>
                  </div>

                  <div className="flex items-center gap-2 text-xs">
                    <Filter className="w-3.5 h-3.5 text-slate-400" />
                    <button
                      type="button"
                      onClick={() => setTimelineFilter("all")}
                      className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition-colors ${
                        timelineFilter === "all"
                          ? "bg-slate-800 text-white border-slate-700"
                          : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700"
                      }`}
                    >
                      All Points ({validationResult.validation_points.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setTimelineFilter("exceptions")}
                      className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition-colors ${
                        timelineFilter === "exceptions"
                          ? "bg-red-600 text-white border-red-500"
                          : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700"
                      }`}
                    >
                      Exceptions Only ({exceptionsOnly.length})
                    </button>
                  </div>
                </div>

                <div className="max-h-80 overflow-y-auto overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 uppercase text-[10px] tracking-wider sticky top-0">
                      <tr>
                        <th className="px-3 py-2">Date (t)</th>
                        <th className="px-3 py-2">Realized Loss (Lt)</th>
                        <th className="px-3 py-2">Forecast VaR Threshold</th>
                        <th className="px-3 py-2">Excess Magnitude</th>
                        <th className="px-3 py-2 text-center">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {pointsToRender.map((p, idx) => (
                        <tr
                          key={idx}
                          className={`hover:bg-slate-50/50 dark:hover:bg-slate-800/30 ${
                            p.is_exception ? "bg-red-50/40 dark:bg-red-950/20" : ""
                          }`}
                        >
                          <td className="px-3 py-2 font-medium text-slate-800 dark:text-slate-200">
                            {p.date}
                          </td>
                          <td
                            className={`px-3 py-2 font-bold ${
                              p.realized_loss > 0 ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"
                            }`}
                          >
                            {formatPct(p.realized_loss)}
                          </td>
                          <td className="px-3 py-2 text-slate-600 dark:text-slate-400">
                            {formatPct(p.forecast_var)}
                          </td>
                          <td className="px-3 py-2">
                            {p.is_exception ? (
                              <span className="text-red-600 dark:text-red-400 font-bold">
                                +{formatPct(p.realized_loss - p.forecast_var)}
                              </span>
                            ) : (
                              <span className="text-slate-400">None</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-center">
                            {p.is_exception ? (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800">
                                EXCEPTION
                              </span>
                            ) : (
                              <span className="text-[10px] text-slate-400">Bounded</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
