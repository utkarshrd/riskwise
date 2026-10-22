import { PieChart } from "lucide-react";
import type { PortfolioRiskMetrics } from "@/lib/api";
import { Card, CardHeader, MetricInfo } from "@/components/ui";

function cellTone(value: number, isSelf: boolean): string {
  if (isSelf) return "bg-slate-100 dark:bg-slate-800 text-slate-500";
  if (value > 0.7) return "bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300";
  if (value > 0.4) return "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300";
  return "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300";
}

export default function CorrelationMatrix({ metrics }: { metrics: PortfolioRiskMetrics }) {
  const { symbols, asset_correlations: corr } = metrics;

  return (
    <Card className="space-y-3">
      <CardHeader
        icon={<PieChart className="w-4 h-4 text-indigo-500" />}
        title={
          <span className="inline-flex items-center gap-1">
            Asset Return Correlation Matrix <MetricInfo metric="correlation" />
          </span>
        }
        right="Pairwise Pearson correlation"
      />
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono text-center">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 text-[11px]">
              <th className="p-2 text-left">Asset</th>
              {symbols.map((s) => (
                <th key={s} className="p-2">
                  {s}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {symbols.map((row) => (
              <tr key={row}>
                <td className="p-2 text-left font-bold text-slate-700 dark:text-slate-300">{row}</td>
                {symbols.map((col) => {
                  const value = corr[row]?.[col];
                  return (
                    <td key={col} className={`p-2 font-semibold ${cellTone(value ?? 0, row === col)}`}>
                      {value != null ? value.toFixed(2) : "N/A"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
