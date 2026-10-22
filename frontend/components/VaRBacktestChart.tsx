"use client";

import { useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { AlertCircle, CheckCircle2, AlertTriangle, ShieldAlert } from "lucide-react";
import { VaRValidationResponse } from "@/lib/api";

interface VaRBacktestChartProps {
  validationResult: VaRValidationResponse;
}

export default function VaRBacktestChart({ validationResult }: VaRBacktestChartProps) {
  const points = useMemo(() => validationResult.validation_points || [], [validationResult.validation_points]);

  // Filter out the exception points for distinct marking
  const exceptions = useMemo(() => {
    return points.filter((p) => p.is_exception);
  }, [points]);

  const chartData = useMemo(() => {
    return points.map((p) => ({
      date: p.date,
      realizedLoss: Number((p.realized_loss * 100).toFixed(2)),
      forecastVaR: Number((p.forecast_var * 100).toFixed(2)),
      isException: p.is_exception,
      exceptionLoss: p.is_exception ? Number((p.realized_loss * 100).toFixed(2)) : null,
    }));
  }, [points]);

  return (
    <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
      {/* Header and Basel Badge */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-indigo-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Out-of-Sample Rolling VaR Backtest ({validationResult.method.toUpperCase()})
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Realized daily losses compared against dynamic 1-day rolling VaR forecasts ({validationResult.confidence_level * 100}% confidence).
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Basel Traffic-Light Badge */}
          <div
            className={`px-3 py-1 rounded-xl text-xs font-bold font-mono flex items-center gap-1.5 border shadow-sm ${
              validationResult.basel_zone === "GREEN"
                ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800"
                : validationResult.basel_zone === "YELLOW"
                ? "bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-800"
                : "bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border-red-300 dark:border-red-800"
            }`}
          >
            {validationResult.basel_zone === "GREEN" ? (
              <CheckCircle2 className="w-3.5 h-3.5" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5" />
            )}
            <span>Basel {validationResult.basel_zone}</span>
            <span className="text-[10px] font-normal opacity-80">
              ({validationResult.basel_capital_multiplier?.toFixed(2) || "3.00"}x mult)
            </span>
          </div>
        </div>
      </div>

      {/* Main Backtest Timeline Chart */}
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 10, right: 15, left: -5, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.4} />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} stroke="#94a3b8" minTickGap={30} />
            <YAxis
              tick={{ fontSize: 10 }}
              stroke="#94a3b8"
              tickFormatter={(val) => `${val}%`}
              label={{ value: "Loss Magnitude %", angle: -90, position: "insideLeft", fontSize: 10, fill: "#94a3b8" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                borderColor: "#334155",
                borderRadius: "0.5rem",
                color: "#f8fafc",
                fontSize: "11px",
              }}
              formatter={(val: number, name: string) => {
                if (name === "Realized Loss") return [`${val.toFixed(2)}%`, name];
                if (name === "Forecast VaR") return [`${val.toFixed(2)}%`, name];
                if (name === "Exception Breach") return [`${val.toFixed(2)}% (Breached!)`, name];
                return [val, name];
              }}
            />
            <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />

            {/* Realized Daily Loss line */}
            <Line
              type="monotone"
              dataKey="realizedLoss"
              name="Realized Loss"
              stroke="#64748b"
              strokeWidth={1.5}
              dot={false}
            />

            {/* Forecast VaR Threshold line */}
            <Line
              type="stepAfter"
              dataKey="forecastVaR"
              name="Forecast VaR"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
            />

            {/* Red Exception Points */}
            <Line
              type="monotone"
              dataKey="exceptionLoss"
              name="Exception Breach"
              stroke="transparent"
              dot={{ r: 4, fill: "#ef4444", stroke: "#b91c1c", strokeWidth: 1.5 }}
              legendType="circle"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Exception Log Table */}
      {exceptions.length > 0 && (
        <div className="pt-2 space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-800 dark:text-slate-200">
            <div className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
              <AlertCircle className="w-4 h-4" />
              <span>Observed Exceedances ({exceptions.length} of {validationResult.forecast_count} days)</span>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              Observed: {(validationResult.exception_rate * 100).toFixed(2)}% vs Nominal: {(validationResult.expected_exception_rate * 100).toFixed(2)}%
            </span>
          </div>

          <div className="max-h-40 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-800">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 border-b border-slate-200 dark:border-slate-800 font-medium">
                <tr>
                  <th className="py-2 px-3">Date</th>
                  <th className="py-2 px-3 text-right">Realized Loss</th>
                  <th className="py-2 px-3 text-right">Forecast VaR</th>
                  <th className="py-2 px-3 text-right">Excess Loss (Breach)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                {exceptions.map((ex, idx) => {
                  const excess = (ex.realized_loss - ex.forecast_var) * 100;
                  return (
                    <tr key={idx} className="hover:bg-rose-50/40 dark:hover:bg-rose-950/20">
                      <td className="py-1.5 px-3 font-semibold text-slate-800 dark:text-slate-200">
                        {ex.date}
                      </td>
                      <td className="py-1.5 px-3 text-right text-rose-600 dark:text-rose-400 font-bold">
                        {(ex.realized_loss * 100).toFixed(2)}%
                      </td>
                      <td className="py-1.5 px-3 text-right text-amber-600 dark:text-amber-400">
                        {(ex.forecast_var * 100).toFixed(2)}%
                      </td>
                      <td className="py-1.5 px-3 text-right text-rose-700 dark:text-rose-300 font-bold">
                        +{excess.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
