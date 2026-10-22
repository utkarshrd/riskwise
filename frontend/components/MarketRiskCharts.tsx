"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Cell,
} from "recharts";
import { TrendingUp, PieChart, Layers, ArrowDownRight } from "lucide-react";
import { PortfolioRiskMetrics } from "@/lib/api";

interface MarketRiskChartsProps {
  metrics: PortfolioRiskMetrics;
  currency: string;
}

export default function MarketRiskCharts({ metrics, currency }: MarketRiskChartsProps) {
  // Series come from the backend and are computed from the portfolio's observed daily returns.
  const series = metrics.chart_series ?? null;

  // 1. Cumulative return vs benchmark (observed, in %)
  const cumulativeData = useMemo(() => {
    if (!series) return [];
    return series.dates.map((date, i) => ({
      date,
      portfolio: series.portfolio_cumulative_pct[i],
      benchmark: series.benchmark_cumulative_pct ? series.benchmark_cumulative_pct[i] : null,
    }));
  }, [series]);

  // 2. Histogram of observed daily portfolio returns, bins shaded by the VaR thresholds
  const histogramData = useMemo(() => {
    if (!series) return [];
    const var95 = metrics.selected_var_95 ?? metrics.historical_var_95;
    const var99 = metrics.selected_var_99 ?? metrics.historical_var_99;
    return series.histogram.map((bin) => {
      const mid = (bin.lo + bin.hi) / 2;
      return {
        range: `${(mid * 100).toFixed(1)}%`,
        frequency: bin.count,
        isVaR95: bin.hi <= -var95,
        isVaR99: bin.hi <= -var99,
      };
    });
  }, [series, metrics]);

  // 3. Drawdown curve (observed, in %)
  const drawdownData = useMemo(() => {
    if (!series) return [];
    return series.dates.map((date, i) => ({ date, drawdown: series.drawdown_pct[i] }));
  }, [series]);

  // 4. Format Component VaR risk attribution data
  const riskAttributionData = useMemo(() => {
    if (!metrics.component_var_pct) {
      // Default to weights if attribution not calculated
      return metrics.symbols.map((sym, idx) => ({
        symbol: sym,
        weight: Number(((metrics.weights[idx] || 0) * 100).toFixed(1)),
        riskContribution: Number(((metrics.weights[idx] || 0) * 100).toFixed(1)),
      }));
    }

    return metrics.symbols.map((sym, idx) => ({
      symbol: sym,
      weight: Number(((metrics.weights[idx] || 0) * 100).toFixed(1)),
      riskContribution: Number(((metrics.component_var_pct?.[sym] || 0) * 100).toFixed(1)),
    }));
  }, [metrics]);

  // 5. Correlation Matrix
  const corrSymbols = metrics.symbols;
  const corrMatrix = metrics.asset_correlations;

  if (!series) {
    return (
      <div className="p-5 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 text-xs text-slate-500">
        Time-series charts are unavailable for this result because the API did not return chart data.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1. Cumulative Return vs Benchmark */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-indigo-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Cumulative Return vs Benchmark ({metrics.benchmark_symbol || (currency === "INR" ? "^NSEI" : "SPY")})
            </h3>
          </div>
          {metrics.beta_to_benchmark != null && (
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 font-mono font-medium border border-indigo-200 dark:border-indigo-800">
              CAPM β: {metrics.beta_to_benchmark.toFixed(2)}
            </span>
          )}
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={cumulativeData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="portGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="benchGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#94a3b8" minTickGap={30} />
              <YAxis
                tick={{ fontSize: 10 }}
                stroke="#94a3b8"
                tickFormatter={(val) => `${val}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  borderColor: "#334155",
                  borderRadius: "0.5rem",
                  color: "#f8fafc",
                  fontSize: "11px",
                }}
                formatter={(val: number) => [`${val.toFixed(2)}%`, ""]}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
              <Area
                type="monotone"
                dataKey="portfolio"
                name="Portfolio Return"
                stroke="#4f46e5"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#portGrad)"
              />
              <Area
                type="monotone"
                dataKey="benchmark"
                connectNulls
                name={`Benchmark (${metrics.benchmark_symbol || (currency === "INR" ? "Nifty 50" : "S&P 500")})`}
                stroke="#10b981"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                fillOpacity={1}
                fill="url(#benchGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Drawdown Underwater Curve & Periods Table */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowDownRight className="w-4 h-4 text-rose-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Rolling Peak-to-Trough Drawdown
            </h3>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 font-mono font-medium border border-rose-200 dark:border-rose-800">
            Max Drawdown: -{(metrics.maximum_drawdown * 100).toFixed(2)}%
          </span>
        </div>

        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={drawdownData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#94a3b8" minTickGap={30} />
              <YAxis
                tick={{ fontSize: 10 }}
                stroke="#94a3b8"
                tickFormatter={(val) => `${val}%`}
                domain={[-Math.ceil(metrics.maximum_drawdown * 120), 0]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  borderColor: "#334155",
                  borderRadius: "0.5rem",
                  color: "#f8fafc",
                  fontSize: "11px",
                }}
                formatter={(val: number) => [`${val.toFixed(2)}%`, "Drawdown"]}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="#f43f5e"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#ddGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Top 5 Historical Drawdown Periods Table */}
        {metrics.drawdown_table && metrics.drawdown_table.length > 0 && (
          <div className="pt-2">
            <div className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-2">
              Top Peak-to-Trough Drawdown Periods
            </div>
            <div className="overflow-x-auto rounded-lg border border-slate-100 dark:border-slate-800">
              <table className="w-full text-left text-[11px]">
                <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-100 dark:border-slate-800">
                  <tr>
                    <th className="py-2 px-3">Peak Date</th>
                    <th className="py-2 px-3">Trough Date</th>
                    <th className="py-2 px-3">Recovery Date</th>
                    <th className="py-2 px-3 text-right">Depth</th>
                    <th className="py-2 px-3 text-right">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                  {metrics.drawdown_table.map((dd, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                      <td className="py-1.5 px-3">{dd.peak_date}</td>
                      <td className="py-1.5 px-3">{dd.trough_date}</td>
                      <td className="py-1.5 px-3 text-slate-400">{dd.recovery_date || "Ongoing"}</td>
                      <td className="py-1.5 px-3 text-right text-rose-600 dark:text-rose-400 font-bold">
                        {(dd.depth * 100).toFixed(2)}%
                      </td>
                      <td className="py-1.5 px-3 text-right text-slate-500">{dd.duration_days} days</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* 3. Return Histogram with VaR / ES Vertical Reference Lines */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Return Distribution & Tail Risk Thresholds ({metrics.selected_var_method?.replace("_", " ").toUpperCase() || "HISTORICAL"})
            </h3>
          </div>
          <div className="flex items-center gap-3 text-[10px] font-mono">
            <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <span className="w-2.5 h-0.5 bg-amber-500"></span> 95% VaR: -{(
                (metrics.selected_var_95 ?? metrics.historical_var_95) * 100
              ).toFixed(2)}%
            </span>
            <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400">
              <span className="w-2.5 h-0.5 bg-rose-500"></span> 99% VaR: -{(
                (metrics.selected_var_99 ?? metrics.historical_var_99) * 100
              ).toFixed(2)}%
            </span>
            <span className="flex items-center gap-1 text-purple-600 dark:text-purple-400">
              <span className="w-2.5 h-0.5 bg-purple-500"></span> 95% ES: -{(
                (metrics.selected_es_95 ?? metrics.expected_shortfall_95) * 100
              ).toFixed(2)}%
            </span>
          </div>
        </div>

        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogramData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} />
              <XAxis dataKey="range" tick={{ fontSize: 9 }} stroke="#94a3b8" interval={2} />
              <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#0f172a",
                  borderColor: "#334155",
                  borderRadius: "0.5rem",
                  color: "#f8fafc",
                  fontSize: "11px",
                }}
                formatter={(val: number) => [val, "Frequency"]}
              />
              <Bar dataKey="frequency" radius={[3, 3, 0, 0]}>
                {histogramData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.isVaR99 ? "#f43f5e" : entry.isVaR95 ? "#f59e0b" : "#4f46e5"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-between items-center text-[10px] text-slate-400">
          <span>← Loss Tail (Negative Returns)</span>
          <span>Observed daily returns</span>
          <span>Gain Tail (Positive Returns) →</span>
        </div>
      </div>

      {/* 4. Risk Attribution & Correlation Heatmap Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Risk Contribution Bars */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <PieChart className="w-4 h-4 text-indigo-500" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Euler Risk Contribution vs Weight
              </h3>
            </div>
            <span className="text-[10px] text-slate-400 font-mono">Component VaR (95%)</span>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={riskAttributionData}
                layout="vertical"
                margin={{ top: 5, right: 20, left: 30, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} />
                <XAxis type="number" tick={{ fontSize: 10 }} stroke="#94a3b8" unit="%" />
                <YAxis dataKey="symbol" type="category" tick={{ fontSize: 10 }} stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    borderColor: "#334155",
                    borderRadius: "0.5rem",
                    color: "#f8fafc",
                    fontSize: "11px",
                  }}
                  formatter={(val: number) => [`${val}%`, ""]}
                />
                <Legend wrapperStyle={{ fontSize: "10px", paddingTop: "4px" }} />
                <Bar dataKey="weight" name="Portfolio Weight %" fill="#94a3b8" radius={[0, 3, 3, 0]} />
                <Bar dataKey="riskContribution" name="Risk Contribution %" fill="#6366f1" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pairwise Asset Correlation Heatmap */}
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-500" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Asset Correlation Heatmap
              </h3>
            </div>
            <span className="text-[10px] text-slate-400 font-mono">Pearson (Adj Close)</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-center text-[10px] font-mono">
              <thead>
                <tr>
                  <th className="p-1"></th>
                  {corrSymbols.map((s) => (
                    <th key={s} className="p-1 font-semibold text-slate-600 dark:text-slate-300 truncate max-w-[60px]">
                      {s.replace(".NS", "")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {corrSymbols.map((rowSym) => (
                  <tr key={rowSym}>
                    <td className="p-1 font-semibold text-slate-600 dark:text-slate-300 text-left truncate max-w-[60px]">
                      {rowSym.replace(".NS", "")}
                    </td>
                    {corrSymbols.map((colSym) => {
                      const val = corrMatrix?.[rowSym]?.[colSym] ?? (rowSym === colSym ? 1.0 : 0.0);
                      // Color mapping: +1.0 = deep indigo/emerald, 0.0 = slate-100, -1.0 = rose
                      const bg =
                        val >= 0.7
                          ? "bg-indigo-600 text-white font-bold"
                          : val >= 0.4
                          ? "bg-indigo-400/80 text-white"
                          : val >= 0.1
                          ? "bg-indigo-100 dark:bg-indigo-950 text-indigo-900 dark:text-indigo-200"
                          : val >= -0.1
                          ? "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                          : "bg-rose-200 dark:bg-rose-950 text-rose-900 dark:text-rose-200";

                      return (
                        <td
                          key={colSym}
                          className={`p-1.5 rounded m-0.5 border border-white dark:border-slate-900 ${bg}`}
                          title={`Correlation between ${rowSym} and ${colSym}: ${val.toFixed(4)}`}
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
      </div>
    </div>
  );
}
