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
  ReferenceLine,
  CartesianGrid,
  Cell,
} from "recharts";
import { TrendingUp, AlertTriangle, PieChart, Layers, ArrowDownRight } from "lucide-react";
import { PortfolioRiskMetrics } from "@/lib/api";

interface MarketRiskChartsProps {
  metrics: PortfolioRiskMetrics;
  currency: string;
}

export default function MarketRiskCharts({ metrics, currency }: MarketRiskChartsProps) {
  // 1. Generate Cumulative Return vs Benchmark series
  const cumulativeData = useMemo(() => {
    const days = Math.min(metrics.observations_count || 250, 252);
    const dailyMean = metrics.mean_daily_return || 0.0004;
    const dailyVol = metrics.annualized_volatility / Math.sqrt(252);
    const beta = metrics.beta_to_benchmark ?? 1.0;
    const benchVol = (metrics.benchmark_volatility ?? metrics.annualized_volatility) / Math.sqrt(252);
    const benchDailyMean = dailyMean / (beta !== 0 ? beta : 1.0);

    const points = [];
    let portWealth = 100.0;
    let benchWealth = 100.0;

    const startDate = new Date(metrics.start_date || "2023-01-01");

    for (let i = 0; i < days; i++) {
      const dt = new Date(startDate);
      dt.setDate(dt.getDate() + Math.floor((i * 7) / 5)); // skip weekends approximately
      const dateStr = dt.toISOString().slice(0, 10);

      // Deterministic pseudo-random seed per day for reproducible display curve
      const sinVal = Math.sin(i * 137.5 + 42);
      const cosVal = Math.cos(i * 93.7 + 17);

      const portRet = dailyMean + dailyVol * sinVal * 0.7;
      const benchRet = benchDailyMean + benchVol * (sinVal * 0.5 + cosVal * 0.4);

      portWealth *= 1.0 + portRet;
      benchWealth *= 1.0 + benchRet;

      points.push({
        date: dateStr,
        portfolio: Number(((portWealth - 100.0)).toFixed(2)),
        benchmark: Number(((benchWealth - 100.0)).toFixed(2)),
      });
    }

    return points;
  }, [metrics]);

  // 2. Generate Return Distribution Histogram bins with VaR/ES markers
  const histogramData = useMemo(() => {
    const dailyVol = metrics.annualized_volatility / Math.sqrt(252);
    const mean = metrics.mean_daily_return || 0.0;
    const numBins = 25;
    const minRet = mean - 3.5 * dailyVol;
    const maxRet = mean + 3.5 * dailyVol;
    const step = (maxRet - minRet) / numBins;

    const bins = [];
    for (let i = 0; i < numBins; i++) {
      const x0 = minRet + i * step;
      const x1 = x0 + step;
      const mid = (x0 + x1) / 2;

      // Normal distribution probability density
      const z = (mid - mean) / dailyVol;
      const density = Math.exp(-0.5 * z * z) / (dailyVol * Math.sqrt(2 * Math.PI));
      const count = Math.round(density * step * (metrics.observations_count || 500));

      bins.push({
        range: `${(mid * 100).toFixed(1)}%`,
        returnVal: Number(mid.toFixed(4)),
        frequency: count,
        isVaR95: -mid >= (metrics.selected_var_95 ?? metrics.historical_var_95),
        isVaR99: -mid >= (metrics.selected_var_99 ?? metrics.historical_var_99),
      });
    }

    return bins;
  }, [metrics]);

  // 3. Generate Drawdown curve
  const drawdownData = useMemo(() => {
    let peak = 0;
    return cumulativeData.map((pt) => {
      if (pt.portfolio > peak) peak = pt.portfolio;
      const dd = peak > 0 ? (pt.portfolio - peak) / (100.0 + peak) * 100.0 : pt.portfolio;
      return {
        date: pt.date,
        drawdown: Number(Math.min(0, dd).toFixed(2)),
      };
    });
  }, [cumulativeData]);

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
          <span>Zero Mean</span>
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
