import { ShieldAlert } from "lucide-react";
import type { PortfolioRiskMetrics, StressScenarioResult } from "@/lib/api";
import { Alert, Card, CardHeader, Skeleton } from "@/components/ui";
import { formatCurrency, formatPct } from "@/lib/format";

interface StressSectionProps {
  metrics: PortfolioRiskMetrics;
  results: StressScenarioResult[] | null;
  loading: boolean;
  error: string | null;
}

export default function StressSection({ metrics, results, loading, error }: StressSectionProps) {
  return (
    <Card className="space-y-4">
      <CardHeader
        className="border-b border-slate-100 dark:border-slate-800 pb-3"
        icon={<ShieldAlert className="w-4 h-4 text-red-500" />}
        title="Historical Stress Tests"
        right="Computed from the portfolio's own price history"
      />

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" role="status" aria-live="polite">
          <span className="sr-only">Evaluating historical stress scenarios…</span>
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
        </div>
      )}

      {error && !loading && (
        <Alert tone="warning" title="Stress tests unavailable">
          {error}
        </Alert>
      )}

      {results && !loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {results.map((s) => (
            <div
              key={s.scenario_name}
              className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-slate-900 dark:text-slate-100">{s.scenario_name.replace(/_/g, " ")}</div>
                  <div className="text-[11px] text-slate-500 mt-0.5">{String(s.assumptions?.description || "")}</div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-sm font-bold text-red-600 dark:text-red-400 font-mono">{formatPct(s.portfolio_loss_pct)}</div>
                  {metrics.portfolio_value && (
                    <div className="text-[10px] text-slate-500 font-mono">
                      -{formatCurrency(Math.abs(s.portfolio_loss_pct * metrics.portfolio_value), metrics.currency)}
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-200/60 dark:border-slate-700/60 space-y-1.5">
                <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">Per-asset shock</div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono">
                  {Object.entries(s.individual_asset_losses).map(([sym, shock]) => (
                    <div key={sym} className="flex justify-between gap-2">
                      <span className="text-slate-600 dark:text-slate-400 truncate">{sym}:</span>
                      <span className="text-red-600 dark:text-red-400 font-medium">{formatPct(shock)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
