import { ShieldAlert } from "lucide-react";
import type { PortfolioRiskMetrics } from "@/lib/api";
import { Card, CardHeader, MetricInfo } from "@/components/ui";
import { formatCurrency, formatPct } from "@/lib/format";
import type { MetricKey } from "@/lib/metric-docs";

interface Row {
  label: string;
  metric: MetricKey;
  confidence: string;
  pct: number;
  amount: number | null | undefined;
  basis: string;
  tone: "indigo" | "red" | "amber";
  shaded?: boolean;
}

const TONE: Record<Row["tone"], string> = {
  indigo: "text-indigo-600 dark:text-indigo-400",
  red: "text-red-600 dark:text-red-400",
  amber: "text-amber-600 dark:text-amber-400",
};

export default function VarTable({ metrics: m }: { metrics: PortfolioRiskMetrics }) {
  const rows: Row[] = [
    { label: "Historical VaR (95%)", metric: "historical_var", confidence: "95.0% (1-in-20)", pct: m.historical_var_95, amount: m.historical_var_95_amount, basis: "Empirical 95th percentile loss", tone: "indigo" },
    { label: "Historical VaR (99%)", metric: "historical_var", confidence: "99.0% (1-in-100)", pct: m.historical_var_99, amount: m.historical_var_99_amount, basis: "Empirical 99th percentile loss", tone: "indigo" },
    { label: "Expected Shortfall (95%)", metric: "expected_shortfall", confidence: "95.0% tail mean", pct: m.expected_shortfall_95, amount: m.expected_shortfall_95_amount, basis: "Mean loss beyond the 95% VaR", tone: "red", shaded: true },
    { label: "Expected Shortfall (99%)", metric: "expected_shortfall", confidence: "99.0% tail mean", pct: m.expected_shortfall_99, amount: m.expected_shortfall_99_amount, basis: "Mean loss beyond the 99% VaR", tone: "red", shaded: true },
    { label: "Parametric VaR (95%)", metric: "parametric_var", confidence: "95.0% Gaussian", pct: m.parametric_var_95, amount: m.parametric_var_95_amount, basis: "z(0.95)·σ − μ, z = 1.645", tone: "amber" },
    { label: "Parametric VaR (99%)", metric: "parametric_var", confidence: "99.0% Gaussian", pct: m.parametric_var_99, amount: m.parametric_var_99_amount, basis: "z(0.99)·σ − μ, z = 2.326", tone: "amber" },
  ];

  return (
    <Card padded={false}>
      <div className="p-4 border-b border-slate-100 dark:border-slate-800">
        <CardHeader
          icon={<ShieldAlert className="w-4 h-4 text-indigo-500" />}
          title="Value at Risk & Expected Shortfall"
          right={<span className="font-mono">1-day holding horizon</span>}
        />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
            <tr>
              <th className="px-4 py-3">Risk Metric</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3 text-right">Loss (%)</th>
              <th className="px-4 py-3 text-right">Loss ({m.currency})</th>
              <th className="px-4 py-3">Basis</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
            {rows.map((r) => (
              <tr
                key={r.label}
                className={`hover:bg-slate-50/50 dark:hover:bg-slate-800/30 ${r.shaded ? "bg-indigo-50/20 dark:bg-indigo-950/10" : ""}`}
              >
                <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                  <span className="inline-flex items-center gap-1">
                    {r.label}
                    <MetricInfo metric={r.metric} />
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600 dark:text-slate-300 whitespace-nowrap">{r.confidence}</td>
                <td className={`px-4 py-3 text-right font-bold ${TONE[r.tone]}`}>{formatPct(r.pct)}</td>
                <td className={`px-4 py-3 text-right font-bold ${r.tone === "red" ? TONE.red : "text-slate-800 dark:text-slate-200"}`}>
                  {formatCurrency(r.amount, m.currency)}
                </td>
                <td className="px-4 py-3 text-slate-500 text-[11px] font-sans">{r.basis}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
