"use client";

import { useState, useEffect, useRef } from "react";
import {
  ShieldAlert,
  RefreshCw,
  Sliders,
  PieChart,
  Activity,
  Info,
  AlertTriangle,
  Trash2,
  DollarSign,
  Calendar,
  CheckCircle2,
  Search,
} from "lucide-react";
import {
  api,
  PortfolioRiskMetrics,
  StressScenarioResult,
  StockSearchResult,
} from "@/lib/api";
import NSEStockSearch from "@/components/NSEStockSearch";
import MarketRiskCharts from "@/components/MarketRiskCharts";

interface HoldingRow {
  symbol: string;
  name?: string;
  exchange?: string;
  currency?: string;
  weight: number;
  position_value?: number;
  state?: "verified_snapshot" | "live_validated" | "not_available" | "validating";
  observations_count?: number;
  alias_note?: string;
}

const PRESET_PORTFOLIOS: Record<
  string,
  { name: string; currency: string; holdings: HoldingRow[]; defaultVal: number }
> = {
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

function formatCurrency(n: number | null | undefined, currency: string) {
  if (n == null) return "N/A";
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency: currency,
    maximumFractionDigits: 0,
  }).format(n);
}

function formatPct(n: number | null | undefined) {
  if (n == null) return "N/A";
  return `${(n * 100).toFixed(2)}%`;
}

export default function MarketRiskPage() {
  const [selectedPreset, setSelectedPreset] = useState<string>("us_tech");
  const [portfolioName, setPortfolioName] = useState<string>("US Tech & Benchmark");
  const [currency, setCurrency] = useState<string>("USD");
  const [portfolioValue, setPortfolioValue] = useState<number>(100000);
  const [inputMode, setInputMode] = useState<"weight" | "value">("weight");
  const [lookbackDays, setLookbackDays] = useState<number>(252);
  const [returnMethod, setReturnMethod] = useState<string>("simple");
  const [varMethod, setVarMethod] = useState<string>("historical");
  const [horizonDays, setHorizonDays] = useState<number>(1);
  const [holdings, setHoldings] = useState<HoldingRow[]>([
    { symbol: "SPY", name: "SPDR S&P 500 ETF", exchange: "NYSE Arca", currency: "USD", weight: 0.4, position_value: 40000 },
    { symbol: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", currency: "USD", weight: 0.3, position_value: 30000 },
    { symbol: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", currency: "USD", weight: 0.3, position_value: 30000 },
  ]);

  // Stock search state
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [showSearchDropdown, setShowSearchDropdown] = useState<boolean>(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  const [supportedSymbols, setSupportedSymbols] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<PortfolioRiskMetrics | null>(null);
  const [stressResults, setStressResults] = useState<StressScenarioResult[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [stressLoading, setStressLoading] = useState<boolean>(false);
  const [refreshLoading, setRefreshLoading] = useState<boolean>(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load universe on mount
  useEffect(() => {
    async function fetchUniverse() {
      try {
        const u = await api.market.universe();
        setSupportedSymbols(u.supported_symbols || []);
      } catch (err) {
        console.warn("Could not fetch market universe:", err);
      }
    }
    fetchUniverse();
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
        console.warn("Stock search error:", err);
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
      setPortfolioValue(p.defaultVal);
      setHoldings(
        p.holdings.map((h) => ({
          ...h,
          position_value: Math.round(h.weight * p.defaultVal),
        }))
      );
      setMetrics(null);
      setStressResults(null);
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
        position_value: Math.round(newWeight * portfolioValue),
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
      } else {
        setSupportedSymbols((prev) => (prev.includes(valRes.canonical_symbol) ? prev : [...prev, valRes.canonical_symbol].sort()));
      }
    } catch (err) {
      console.warn("Symbol validation error:", err);
    }
  };

  const handleHoldingChange = (
    index: number,
    field: "symbol" | "weight" | "position_value",
    val: string | number
  ) => {
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
        const w = Number(val);
        updated[index] = {
          ...updated[index],
          weight: w,
          position_value: Math.round(w * portfolioValue),
        };
      } else if (field === "position_value") {
        const pv = Number(val);
        updated[index] = { ...updated[index], position_value: pv };
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
  const totalPositionValue = holdings.reduce((sum, h) => sum + (h.position_value || 0), 0);

  const normalizeWeights = () => {
    if (inputMode === "value" && totalPositionValue > 0) {
      setHoldings((prev) =>
        prev.map((h) => ({
          ...h,
          weight: Number(((h.position_value || 0) / totalPositionValue).toFixed(4)),
        }))
      );
      setPortfolioValue(totalPositionValue);
    } else if (totalWeight > 0) {
      setHoldings((prev) =>
        prev.map((h) => ({
          ...h,
          weight: Number((h.weight / totalWeight).toFixed(4)),
          position_value: Math.round((h.weight / totalWeight) * portfolioValue),
        }))
      );
    }
  };

  // Currency validation
  const assetCurrencies = holdings.map((h) => h.currency || inferSymbolCurrency(h.symbol));
  const distinctCurrencies = Array.from(new Set(assetCurrencies));
  const hasMixedCurrencies = distinctCurrencies.length > 1;
  const portfolioCurrencyMismatch = !hasMixedCurrencies && distinctCurrencies[0] && distinctCurrencies[0] !== currency;

  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const payloadHoldings =
        inputMode === "value"
          ? holdings.map((h) => ({ symbol: h.symbol, position_value: h.position_value }))
          : holdings.map((h) => ({ symbol: h.symbol, weight: Number(h.weight) }));

      const res = await api.market.analyze({
        holdings: payloadHoldings,
        portfolio_name: portfolioName,
        currency,
        lookback_days: lookbackDays,
        return_method: returnMethod,
        portfolio_value: portfolioValue,
        var_method: varMethod,
        horizon_days: horizonDays,
      });
      setMetrics(res);

      // Also trigger stress tests
      setStressLoading(true);
      try {
        const stress = await api.market.stressTest(payloadHoldings);
        setStressResults(stress);
      } catch (stErr) {
        console.warn("Stress test error:", stErr);
      } finally {
        setStressLoading(false);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Portfolio analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshMarketData = async (live: boolean) => {
    setRefreshLoading(true);
    setRefreshMessage(null);
    try {
      const res = await api.market.refresh({ fetch_live: live });
      setRefreshMessage(
        live && res.data_source_mode === "live_refreshed"
          ? `Live refresh successful via Yahoo Finance (${res.refreshed_at.slice(0, 19)}Z).`
          : `Snapshot audited successfully (${res.supported_symbols.length} tickers verified). Mode: ${res.data_source_mode}.`
      );
      // Reload universe
      const u = await api.market.universe();
      setSupportedSymbols(u.supported_symbols || []);
    } catch (err: unknown) {
      setRefreshMessage(err instanceof Error ? `Refresh error: ${err.message}` : "Refresh failed.");
    } finally {
      setRefreshLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-1 tracking-wide uppercase">
            <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800">
              Quantitative Market Risk
            </span>
            <span className="text-slate-400">•</span>
            <span>Single-Currency Portfolios</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Portfolio Market Risk Lab
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
            Empirical Historical VaR, Gaussian Parametric VaR, Expected Shortfall (CVaR), 252-day volatility, correlation analysis, and empirical worst-window stress tests.
          </p>
        </div>

        {/* Data Provenance & Refresh actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleRefreshMarketData(false)}
            disabled={refreshLoading}
            className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 flex items-center gap-1.5 transition-colors disabled:opacity-50"
            title="Verify local CSV price snapshots and manifest checksums"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshLoading ? "animate-spin" : ""}`} />
            Audit Snapshots
          </button>
          <button
            onClick={() => handleRefreshMarketData(true)}
            disabled={refreshLoading}
            className="px-3 py-2 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
            title="Attempt live price update from Yahoo Finance"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshLoading ? "animate-spin" : ""}`} />
            Live Yahoo Refresh
          </button>
        </div>
      </div>

      {refreshMessage && (
        <div className="p-3.5 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/70 dark:bg-indigo-950/40 text-xs text-indigo-900 dark:text-indigo-200 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
          <span>{refreshMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl border border-red-200 dark:border-red-900/60 bg-red-50/80 dark:bg-red-950/40 text-sm text-red-900 dark:text-red-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-semibold">Validation or Calculation Error</div>
            <div className="text-xs leading-relaxed">{error}</div>
          </div>
        </div>
      )}

      {/* Main Grid: Inputs on Left, Analytics on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Portfolio Configuration */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                <Sliders className="w-4 h-4 text-indigo-500" />
                <span>Portfolio Setup</span>
              </div>
              <span className="text-[11px] font-mono text-slate-500">
                {currency} • {holdings.length} Assets
              </span>
            </div>

            {/* Presets */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                Benchmark Presets
              </label>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(PRESET_PORTFOLIOS).map(([key, p]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handleSelectPreset(key)}
                    className={`text-left p-2.5 rounded-lg border text-xs transition-all ${
                      selectedPreset === key
                        ? "border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200 font-medium"
                        : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 text-slate-600 dark:text-slate-400"
                    }`}
                  >
                    <div className="font-semibold text-slate-800 dark:text-slate-200 text-[11px] truncate">
                      {p.name}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      {p.currency} • {p.holdings.map((h) => h.symbol).join(", ")}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Name & Base Currency */}
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2 space-y-1">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Portfolio Label
                </label>
                <input
                  type="text"
                  value={portfolioName}
                  onChange={(e) => setPortfolioName(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Currency
                </label>
                <select
                  value={currency}
                  onChange={(e) => {
                    setCurrency(e.target.value);
                    setSelectedPreset("custom");
                  }}
                  className="w-full text-xs px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="USD">USD ($)</option>
                  <option value="INR">INR (₹)</option>
                </select>
              </div>
            </div>

            {/* Monetary Portfolio Value */}
            <div className="space-y-1">
              <div className="flex justify-between items-center text-xs">
                <label className="font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1">
                  <DollarSign className="w-3.5 h-3.5 text-slate-400" />
                  Portfolio Monetary Value ({currency})
                </label>
                <div className="flex items-center gap-1 text-[11px] text-slate-500">
                  <button
                    type="button"
                    onClick={() => setInputMode("weight")}
                    className={`px-1.5 py-0.5 rounded ${
                      inputMode === "weight"
                        ? "bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-semibold"
                        : "hover:text-slate-800"
                    }`}
                  >
                    By Weight
                  </button>
                  <span>|</span>
                  <button
                    type="button"
                    onClick={() => setInputMode("value")}
                    className={`px-1.5 py-0.5 rounded ${
                      inputMode === "value"
                        ? "bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-semibold"
                        : "hover:text-slate-800"
                    }`}
                  >
                    By Value
                  </button>
                </div>
              </div>
              <input
                type="number"
                min="1000"
                step="5000"
                value={portfolioValue}
                onChange={(e) => setPortfolioValue(Number(e.target.value))}
                className="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
              />
            </div>

            {/* Stock Search with Sector & Index Chips */}
            <div className="space-y-1.5">
              <NSEStockSearch
                onSelectSymbol={(sym, name, curr) => addAssetToPortfolio({ symbol: sym, name, currency: curr })}
                activeCurrency={currency}
                disabledSymbols={holdings.map((h) => h.symbol)}
              />
            </div>

            {/* Asset Holdings Table */}
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

              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
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

                      {/* Weight / Value Input */}
                      <div className="pt-0.5">
                        {inputMode === "weight" ? (
                          <div className="flex items-center gap-1.5">
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
                            <span className="text-[10px] text-slate-400 font-mono shrink-0 w-20 text-right">
                              {formatCurrency(h.weight * portfolioValue, currency)}
                            </span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number"
                              step="5000"
                              min="100"
                              value={h.position_value || 0}
                              onChange={(e) =>
                                handleHoldingChange(idx, "position_value", e.target.value)
                              }
                              className="w-full text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-mono"
                            />
                            <span className="text-[10px] text-slate-400 font-mono shrink-0 w-12 text-right">
                              {totalPositionValue > 0
                                ? `${(((h.position_value || 0) / totalPositionValue) * 100).toFixed(1)}%`
                                : "0%"}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-slate-400">
                  {holdings.length} asset{holdings.length !== 1 ? "s" : ""} selected
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
                  <strong>{distinctCurrencies.join(" and ")}</strong>. RiskWise enforces strict single-currency portfolios without synthetic FX assumptions. Please retain only INR or only USD assets.
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

            {/* Parameters */}
            <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-400" />
                  Lookback Period
                </label>
                <select
                  value={lookbackDays}
                  onChange={(e) => setLookbackDays(Number(e.target.value))}
                  className="w-full text-xs px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                >
                  <option value={60}>60 Trading Days</option>
                  <option value={120}>120 Trading Days</option>
                  <option value={252}>252 Days (1 Year)</option>
                  <option value={500}>500 Days (2 Years)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Return Formulation
                </label>
                <select
                  value={returnMethod}
                  onChange={(e) => setReturnMethod(e.target.value)}
                  className="w-full text-xs px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                >
                  <option value="simple">Discrete Simple Returns</option>
                  <option value="log">Log Returns (ln(P_t/P_0))</option>
                </select>
              </div>

              {/* VaR Model Selector */}
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  VaR Model
                </label>
                <select
                  value={varMethod}
                  onChange={(e) => setVarMethod(e.target.value)}
                  className="w-full text-xs px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-medium"
                >
                  <option value="historical">Historical Quantile (Empirical)</option>
                  <option value="gaussian">Gaussian Parametric (Normal)</option>
                  <option value="student_t">Student-t (Fat Tails)</option>
                  <option value="cornish_fisher">Cornish-Fisher (Skew/Kurtosis)</option>
                  <option value="ewma">EWMA (RiskMetrics λ=0.94)</option>
                  <option value="monte_carlo">Monte Carlo (Cholesky Seeded)</option>
                  <option value="garch">GARCH(1,1) Volatility</option>
                  <option value="fhs">Filtered Historical Simulation</option>
                </select>
              </div>

              {/* Horizon Days Selector */}
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Holding Horizon
                </label>
                <select
                  value={horizonDays}
                  onChange={(e) => setHorizonDays(Number(e.target.value))}
                  className="w-full text-xs px-2.5 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-mono"
                >
                  <option value={1}>1 Trading Day (Daily)</option>
                  <option value={5}>5 Trading Days (1 Week)</option>
                  <option value={10}>10 Trading Days (Basel)</option>
                  <option value={20}>20 Trading Days (1 Month)</option>
                </select>
              </div>
            </div>

            {/* Submit Action */}
            <button
              type="button"
              onClick={handleRunAnalysis}
              disabled={loading || hasMixedCurrencies || holdings.length === 0}
              className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
            >
              <Activity className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              {loading
                ? "Computing Risk Metrics..."
                : hasMixedCurrencies
                ? "Resolve Currency Mismatch to Proceed"
                : "Run Portfolio Risk Assessment"}
            </button>
          </div>

          {/* Universe Guidance Card */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400 space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
                <Info className="w-4 h-4 text-indigo-500" />
                <span>Preloaded Offline Snapshots (Instant)</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-medium">
                {supportedSymbols.length} Cached
              </span>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              These preloaded instruments are cached locally with split/dividend-adjusted historical prices (<code>adj_close</code>) for instantaneous calculation.
              <strong className="block text-slate-700 dark:text-slate-300 mt-1">
                You can search or enter ANY other NSE/BSE/US equity above — new symbols are validated and retrieved on-the-fly.
              </strong>
            </p>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {supportedSymbols.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => addAssetToPortfolio({ symbol: s })}
                  className="px-2 py-0.5 rounded bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:border-indigo-300 dark:hover:border-indigo-700 border border-slate-200 dark:border-slate-700 font-mono text-[10px] transition-colors cursor-pointer text-slate-700 dark:text-slate-300"
                  title="Click to add to portfolio"
                >
                  + {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Risk Analytics Results */}
        <div className="lg:col-span-7 space-y-6">
          {!metrics && !loading && (
            <div className="p-12 rounded-xl border border-dashed border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/40 text-center space-y-4">
              <div className="inline-flex p-3 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400">
                <PieChart className="w-8 h-8" />
              </div>
              <div className="max-w-sm mx-auto space-y-1">
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                  Ready to Calculate Risk
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  Configure portfolio holdings on the left and click <strong>Run Portfolio Risk Assessment</strong> to compute empirical VaR, CVaR, drawdown, and correlation matrix.
                </p>
              </div>
            </div>
          )}

          {metrics && (
            <div className="space-y-6">
              {/* Top Banner: Observations and Provenance */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-slate-900 dark:text-slate-100">
                    {metrics.portfolio_name}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-mono text-[11px]">
                    {metrics.observations_count} Aligned Days
                  </span>
                  <span className="text-slate-400">•</span>
                  <span className="text-slate-500 font-mono">
                    {metrics.start_date} to {metrics.end_date}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                    Source: {metrics.data_source_mode === "live_refreshed" ? "Live Yahoo API" : "Verified Snapshot"}
                  </span>
                </div>
              </div>

              {/* Methodology & Loss Convention Alert */}
              <div className="p-3.5 rounded-xl border border-indigo-100 dark:border-indigo-950 bg-indigo-50/50 dark:bg-indigo-950/20 text-xs text-indigo-900 dark:text-indigo-200 flex items-start gap-2.5">
                <Info className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong>Loss Convention:</strong> Loss is expressed as a positive magnitude (<code className="font-mono">L = -R</code>). A 95% 1-day VaR of 2.14% signifies a 5% historical probability that the daily portfolio loss exceeds 2.14%.
                </div>
              </div>

              {/* Core Risk Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Annualized Volatility
                  </div>
                  <div className="text-lg font-bold text-slate-900 dark:text-slate-100 font-mono">
                    {formatPct(metrics.annualized_volatility)}
                  </div>
                  <div className="text-[10px] text-slate-400">√252 Trading Days</div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Maximum Drawdown
                  </div>
                  <div className="text-lg font-bold text-red-600 dark:text-red-400 font-mono">
                    {formatPct(metrics.maximum_drawdown)}
                  </div>
                  <div className="text-[10px] text-slate-400">Peak-to-Trough</div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Mean Daily Return
                  </div>
                  <div
                    className={`text-lg font-bold font-mono ${
                      metrics.mean_daily_return >= 0
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {(metrics.mean_daily_return * 100).toFixed(3)}%
                  </div>
                  <div className="text-[10px] text-slate-400">Per Session Drift</div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Portfolio Value
                  </div>
                  <div className="text-lg font-bold text-slate-900 dark:text-slate-100 font-mono truncate">
                    {metrics.portfolio_value
                      ? formatCurrency(metrics.portfolio_value, metrics.currency)
                      : "Unspecified"}
                  </div>
                  <div className="text-[10px] text-slate-400">Base Currency: {metrics.currency}</div>
                </div>

                {/* Performance & Factor Ratios */}
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Sharpe Ratio (Rf=0%)
                  </div>
                  <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400 font-mono">
                    {metrics.sharpe_ratio != null ? metrics.sharpe_ratio.toFixed(2) : "N/A"}
                  </div>
                  <div className="text-[10px] text-slate-400">Risk-Adjusted Return</div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Sortino Ratio
                  </div>
                  <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400 font-mono">
                    {metrics.sortino_ratio != null ? metrics.sortino_ratio.toFixed(2) : "N/A"}
                  </div>
                  <div className="text-[10px] text-slate-400">Downside Semi-Deviation</div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Beta vs {metrics.benchmark_symbol || "Benchmark"}
                  </div>
                  <div className="text-lg font-bold text-slate-900 dark:text-slate-100 font-mono">
                    {metrics.beta_to_benchmark != null ? metrics.beta_to_benchmark.toFixed(2) : "1.00"}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Corr: {metrics.correlation_to_benchmark != null ? metrics.correlation_to_benchmark.toFixed(2) : "1.00"}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1">
                  <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Active VaR Method
                  </div>
                  <div className="text-sm font-bold text-emerald-600 dark:text-emerald-400 font-mono uppercase truncate pt-1">
                    {(metrics.selected_var_method || varMethod).replace(/_/g, " ")}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">Horizon: {metrics.horizon_days || horizonDays}D</div>
                </div>
              </div>

              {/* Value-at-Risk & Expected Shortfall Comparison Table */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-sm">
                <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-indigo-500" />
                    <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      Value-at-Risk & Expected Shortfall (CVaR)
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-500 font-mono">1-Day Holding Horizon</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
                      <tr>
                        <th className="px-4 py-3">Risk Metric</th>
                        <th className="px-4 py-3">Confidence Level</th>
                        <th className="px-4 py-3 text-right">Percentage Loss (%)</th>
                        <th className="px-4 py-3 text-right">
                          Currency Loss ({metrics.currency})
                        </th>
                        <th className="px-4 py-3">Methodology Basis</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                      {/* Historical VaR 95 */}
                      <tr className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                        <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">
                          Historical VaR (95%)
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">95.0% (1-in-20)</td>
                        <td className="px-4 py-3 text-right text-indigo-600 dark:text-indigo-400 font-bold">
                          {formatPct(metrics.historical_var_95)}
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-slate-800 dark:text-slate-200">
                          {formatCurrency(metrics.historical_var_95_amount, metrics.currency)}
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-[11px] font-sans">
                          Empirical 95th Percentile Loss
                        </td>
                      </tr>

                      {/* Historical VaR 99 */}
                      <tr className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                        <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">
                          Historical VaR (99%)
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">99.0% (1-in-100)</td>
                        <td className="px-4 py-3 text-right text-indigo-600 dark:text-indigo-400 font-bold">
                          {formatPct(metrics.historical_var_99)}
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-slate-800 dark:text-slate-200">
                          {formatCurrency(metrics.historical_var_99_amount, metrics.currency)}
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-[11px] font-sans">
                          Empirical 99th Percentile Loss
                        </td>
                      </tr>

                      {/* Expected Shortfall 95 */}
                      <tr className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 bg-indigo-50/20 dark:bg-indigo-950/10">
                        <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">
                          Expected Shortfall (CVaR 95%)
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">95.0% Tail Mean</td>
                        <td className="px-4 py-3 text-right text-red-600 dark:text-red-400 font-bold">
                          {formatPct(metrics.expected_shortfall_95)}
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-red-600 dark:text-red-400">
                          {formatCurrency(metrics.expected_shortfall_95_amount, metrics.currency)}
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-[11px] font-sans">
                          Mean Loss Beyond 95% VaR Threshold
                        </td>
                      </tr>

                      {/* Expected Shortfall 99 */}
                      <tr className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 bg-indigo-50/20 dark:bg-indigo-950/10">
                        <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">
                          Expected Shortfall (CVaR 99%)
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">99.0% Tail Mean</td>
                        <td className="px-4 py-3 text-right text-red-600 dark:text-red-400 font-bold">
                          {formatPct(metrics.expected_shortfall_99)}
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-red-600 dark:text-red-400">
                          {formatCurrency(metrics.expected_shortfall_99_amount, metrics.currency)}
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-[11px] font-sans">
                          Mean Loss Beyond 99% VaR Threshold
                        </td>
                      </tr>

                      {/* Parametric VaR 95 */}
                      <tr className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                        <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">
                          Parametric VaR (95%)
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">95.0% Gaussian</td>
                        <td className="px-4 py-3 text-right text-amber-600 dark:text-amber-400 font-bold">
                          {formatPct(metrics.parametric_var_95)}
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-slate-800 dark:text-slate-200">
                          {formatCurrency(metrics.parametric_var_95_amount, metrics.currency)}
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-[11px] font-sans">
                          Gaussian: z(0.95)*σ - μ (z=1.645)
                        </td>
                      </tr>

                      {/* Parametric VaR 99 */}
                      <tr className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                        <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">
                          Parametric VaR (99%)
                        </td>
                        <td className="px-4 py-3 text-slate-600 dark:text-slate-300">99.0% Gaussian</td>
                        <td className="px-4 py-3 text-right text-amber-600 dark:text-amber-400 font-bold">
                          {formatPct(metrics.parametric_var_99)}
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-slate-800 dark:text-slate-200">
                          {formatCurrency(metrics.parametric_var_99_amount, metrics.currency)}
                        </td>
                        <td className="px-4 py-3 text-slate-500 text-[11px] font-sans">
                          Gaussian: z(0.99)*σ - μ (z=2.326)
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Dynamic Interactive Recharts Visualizations (A5) */}
              <MarketRiskCharts metrics={metrics} currency={metrics.currency} />

              {/* Correlation Matrix Heatmap */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <PieChart className="w-4 h-4 text-indigo-500" />
                    <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      Asset Return Correlation Matrix
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">Pairwise Pearson Correlation</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono text-center">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 text-[11px]">
                        <th className="p-2 text-left">Asset</th>
                        {metrics.symbols.map((s) => (
                          <th key={s} className="p-2">
                            {s}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {metrics.symbols.map((rowSym) => (
                        <tr key={rowSym} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                          <td className="p-2 text-left font-bold text-slate-700 dark:text-slate-300">
                            {rowSym}
                          </td>
                          {metrics.symbols.map((colSym) => {
                            const val = metrics.asset_correlations[rowSym]?.[colSym] ?? 1.0;
                            const isSelf = rowSym === colSym;
                            return (
                              <td
                                key={colSym}
                                className={`p-2 font-semibold ${
                                  isSelf
                                    ? "bg-slate-100 dark:bg-slate-800 text-slate-500"
                                    : val > 0.7
                                    ? "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300"
                                    : val > 0.4
                                    ? "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300"
                                    : "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300"
                                }`}
                              >
                                {val.toFixed(2)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Stress Scenarios Section */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-red-500" />
                    <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      Historical Empirical Stress Tests
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">Zero Fabricated Numbers</span>
                </div>

                {stressLoading && (
                  <div className="text-center py-6 text-xs text-slate-500 animate-pulse">
                    Evaluating empirical scenario shocks...
                  </div>
                )}

                {stressResults && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {stressResults.map((s, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-3"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                              {s.scenario_name.replace(/_/g, " ")}
                            </div>
                            <div className="text-[11px] text-slate-500 mt-0.5">
                              {String(s.assumptions?.description || "")}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-bold text-red-600 dark:text-red-400 font-mono">
                              {formatPct(s.portfolio_loss_pct)}
                            </div>
                            {metrics.portfolio_value && (
                              <div className="text-[10px] text-slate-500 font-mono">
                                -{formatCurrency(
                                  Math.abs(s.portfolio_loss_pct * metrics.portfolio_value),
                                  metrics.currency
                                )}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Individual asset contributions */}
                        <div className="pt-2 border-t border-slate-200/60 dark:border-slate-700/60 space-y-1.5">
                          <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                            Asset Empirical Shock
                          </div>
                          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono">
                            {Object.entries(s.individual_asset_losses).map(([sym, shock]) => (
                              <div key={sym} className="flex justify-between">
                                <span className="text-slate-600 dark:text-slate-400">{sym}:</span>
                                <span className="text-red-600 dark:text-red-400 font-medium">
                                  {formatPct(shock)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
