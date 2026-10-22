import type { PortfolioRiskMetrics } from "@/lib/api";
import { Stat } from "@/components/ui";
import { formatCurrency, formatNumber, formatPct } from "@/lib/format";
import { VAR_METHOD_METRIC } from "@/lib/metric-docs";

export default function MetricGrid({ metrics }: { metrics: PortfolioRiskMetrics }) {
  const rf = metrics.assumptions?.risk_free_rate;
  const rfNote = typeof rf === "number" ? `Risk-free ${(rf * 100).toFixed(1)}% p.a.` : "Risk-adjusted return";
  const method = metrics.selected_var_method ?? "historical";

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Stat label="Annualized Volatility" metric="annualized_volatility" value={formatPct(metrics.annualized_volatility)} hint="√252 trading days" />
      <Stat label="Maximum Drawdown" metric="max_drawdown" tone="bad" value={formatPct(metrics.maximum_drawdown)} hint="Peak to trough" />
      <Stat
        label="Mean Daily Return"
        metric="mean_daily_return"
        tone={metrics.mean_daily_return >= 0 ? "good" : "bad"}
        value={`${(metrics.mean_daily_return * 100).toFixed(3)}%`}
        hint="Per session drift"
      />
      <Stat
        label="Portfolio Value"
        value={metrics.portfolio_value ? formatCurrency(metrics.portfolio_value, metrics.currency) : "Unspecified"}
        hint={`Base currency: ${metrics.currency}`}
      />
      <Stat label="Sharpe Ratio" metric="sharpe" tone="accent" value={formatNumber(metrics.sharpe_ratio)} hint={rfNote} />
      <Stat label="Sortino Ratio" metric="sortino" tone="accent" value={formatNumber(metrics.sortino_ratio)} hint="Downside deviation only" />
      <Stat
        label={`Beta vs ${metrics.benchmark_symbol || "benchmark"}`}
        metric="beta"
        value={metrics.beta_to_benchmark != null ? metrics.beta_to_benchmark.toFixed(2) : "N/A"}
        hint={metrics.correlation_to_benchmark != null ? `Correlation ${metrics.correlation_to_benchmark.toFixed(2)}` : "No benchmark data"}
      />
      <Stat
        label="Active VaR Method"
        metric={VAR_METHOD_METRIC[method] ?? "historical_var"}
        tone="good"
        value={<span className="text-sm uppercase">{method.replace(/_/g, " ")}</span>}
        hint={`Horizon: ${metrics.horizon_days ?? 1} day${(metrics.horizon_days ?? 1) === 1 ? "" : "s"}`}
      />
    </div>
  );
}
