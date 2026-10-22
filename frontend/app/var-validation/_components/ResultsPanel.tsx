import { ShieldCheck } from "lucide-react";
import VaRBacktestChart from "@/components/VaRBacktestChart";
import VaRModelComparison from "@/components/VaRModelComparison";
import { EmptyState, ResultsSkeleton } from "@/components/ui";
import type { VaRValidationResponse } from "@/lib/api";
import CoverageTests from "./CoverageTests";
import ExceptionTimeline from "./ExceptionTimeline";
import SummaryStats from "./SummaryStats";

interface ResultsPanelProps {
  result: VaRValidationResponse | null;
  loading: boolean;
  holdings: Array<{ symbol: string; weight: number }>;
  currency: string;
  confidenceLevel: number;
  lookbackWindow: number;
  method: string;
  onSelectMethod: (method: string) => void;
}

export default function ResultsPanel({
  result,
  loading,
  holdings,
  currency,
  confidenceLevel,
  lookbackWindow,
  method,
  onSelectMethod,
}: ResultsPanelProps) {
  if (loading) return <ResultsSkeleton label="Running the rolling backtest" />;

  if (!result) {
    return (
      <EmptyState
        icon={<ShieldCheck className="w-8 h-8" />}
        title="Ready to run a backtest"
        description={
          <>
            Choose a portfolio and click <strong>Execute Rolling VaR Validation</strong>. The engine slides the estimation window forward one day at a time, forecasts VaR, and tests coverage (Kupiec) and exception clustering (Christoffersen).
          </>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <SummaryStats result={result} />
      <VaRBacktestChart validationResult={result} />
      <VaRModelComparison
        holdings={holdings}
        currency={currency}
        confidenceLevel={confidenceLevel}
        lookbackWindow={lookbackWindow}
        onSelectMethod={onSelectMethod}
        activeMethod={method}
      />
      <CoverageTests result={result} />
      <ExceptionTimeline result={result} />
    </div>
  );
}
