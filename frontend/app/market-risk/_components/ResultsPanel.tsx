import { PieChart } from "lucide-react";
import MarketRiskCharts from "@/components/MarketRiskCharts";
import { Alert, Badge, EmptyState, ResultsSkeleton } from "@/components/ui";
import type { PortfolioRiskMetrics, StressScenarioResult } from "@/lib/api";
import CorrelationMatrix from "./CorrelationMatrix";
import MetricGrid from "./MetricGrid";
import StressSection from "./StressSection";
import VarTable from "./VarTable";

interface ResultsPanelProps {
  metrics: PortfolioRiskMetrics | null;
  loading: boolean;
  stressResults: StressScenarioResult[] | null;
  stressLoading: boolean;
  stressError: string | null;
}

function sourceLabel(mode?: string): string {
  if (mode === "live_refreshed" || mode === "live_download") return "Live Yahoo Finance";
  return "Verified snapshot";
}

export default function ResultsPanel({ metrics, loading, stressResults, stressLoading, stressError }: ResultsPanelProps) {
  if (loading) return <ResultsSkeleton label="Computing risk metrics" />;

  if (!metrics) {
    return (
      <EmptyState
        icon={<PieChart className="w-8 h-8" />}
        title="Ready to Calculate Risk"
        description={
          <>
            Configure the portfolio and click <strong>Run Portfolio Risk Assessment</strong> to compute VaR, expected shortfall, drawdown and correlation.
          </>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 min-w-0">
          <span className="font-semibold text-slate-900 dark:text-slate-100 truncate">{metrics.portfolio_name}</span>
          <Badge tone="green" className="font-mono">
            {metrics.observations_count} aligned days
          </Badge>
          <span className="text-slate-500 font-mono">
            {metrics.start_date} to {metrics.end_date}
          </span>
        </div>
        <Badge>Source: {sourceLabel(metrics.data_source_mode)}</Badge>
      </div>

      <Alert tone="info">
        <strong>Loss convention:</strong> a loss is a positive number. A 95% 1-day VaR of 2.14% means that on about 5% of days the portfolio loses more than 2.14%.
      </Alert>

      <MetricGrid metrics={metrics} />
      <VarTable metrics={metrics} />
      <MarketRiskCharts metrics={metrics} currency={metrics.currency} />
      <CorrelationMatrix metrics={metrics} />
      <StressSection metrics={metrics} results={stressResults} loading={stressLoading} error={stressError} />
    </div>
  );
}
