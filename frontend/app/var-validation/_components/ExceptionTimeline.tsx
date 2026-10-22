"use client";

import { useState } from "react";
import type { VaRValidationResponse } from "@/lib/api";
import { Card, Tabs } from "@/components/ui";
import { formatPct } from "@/lib/format";

type Filter = "all" | "exceptions";

export default function ExceptionTimeline({ result }: { result: VaRValidationResponse }) {
  const [filter, setFilter] = useState<Filter>("all");
  const exceptions = result.validation_points.filter((p) => p.is_exception);
  const rows = filter === "exceptions" ? exceptions : result.validation_points;

  return (
    <Card className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Out-of-Sample Forecasts vs Realized Losses</h4>
          <p className="text-xs text-slate-500 dark:text-slate-400">An exception is a day when the realized loss (L = −R) exceeds the forecast VaR.</p>
        </div>
        <Tabs
          ariaLabel="Filter forecast days"
          value={filter}
          onChange={setFilter}
          tabs={[
            { id: "all", label: `All points (${result.validation_points.length})` },
            { id: "exceptions", label: `Exceptions only (${exceptions.length})` },
          ]}
        />
      </div>

      {rows.length === 0 ? (
        <p className="text-xs text-slate-400 py-4 text-center">No exceptions in this window.</p>
      ) : (
        <div className="max-h-80 overflow-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 uppercase text-[10px] tracking-wider sticky top-0">
              <tr>
                <th className="px-3 py-2">Date (t)</th>
                <th className="px-3 py-2">Realized loss</th>
                <th className="px-3 py-2">Forecast VaR</th>
                <th className="px-3 py-2">Excess</th>
                <th className="px-3 py-2 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {rows.map((p) => (
                <tr key={p.date} className={`hover:bg-slate-50/50 dark:hover:bg-slate-800/30 ${p.is_exception ? "bg-red-50/40 dark:bg-red-950/20" : ""}`}>
                  <td className="px-3 py-2 font-medium text-slate-800 dark:text-slate-200">{p.date}</td>
                  <td className={`px-3 py-2 font-bold ${p.realized_loss > 0 ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                    {formatPct(p.realized_loss)}
                  </td>
                  <td className="px-3 py-2 text-slate-600 dark:text-slate-400">{formatPct(p.forecast_var)}</td>
                  <td className="px-3 py-2">
                    {p.is_exception ? (
                      <span className="text-red-600 dark:text-red-400 font-bold">+{formatPct(p.realized_loss - p.forecast_var)}</span>
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
                      <span className="text-[10px] text-slate-400">Within VaR</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
