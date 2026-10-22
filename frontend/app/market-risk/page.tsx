"use client";

import { useMemo } from "react";
import { Alert } from "@/components/ui";
import { usePortfolioBuilder } from "@/hooks/usePortfolioBuilder";
import MarketHeader from "./_components/MarketHeader";
import PortfolioForm from "./_components/PortfolioForm";
import ResultsPanel from "./_components/ResultsPanel";
import UniverseCard from "./_components/UniverseCard";
import { useMarketUniverse } from "./_hooks/useMarketUniverse";
import { useAnalysisParams } from "./_hooks/useAnalysisParams";
import { useRiskAnalysis } from "./_hooks/useRiskAnalysis";
import { DEFAULT_PRESET, PRESET_PORTFOLIOS } from "./_lib/options";

export default function MarketRiskPage() {
  const universe = useMarketUniverse();
  const analysis = useRiskAnalysis();

  const params = useAnalysisParams();
  const builder = usePortfolioBuilder({
    presets: PRESET_PORTFOLIOS,
    defaultPreset: DEFAULT_PRESET,
    onProblem: analysis.setError,
    onSymbolVerified: universe.addSymbol,
    onPortfolioReset: analysis.reset,
  });

  // Same portfolio as the results on screen, so the stress lab always matches what the user is looking at
  const req = analysis.request;
  const stressInput = useMemo(
    () =>
      req
        ? { holdings: req.holdings, currency: req.currency, fx_mode: req.fx_mode, portfolio_value: req.portfolio_value }
        : null,
    [req]
  );

  const runAnalysis = () =>
    analysis.run({
      holdings: builder.payloadHoldings(),
      portfolio_name: builder.portfolioName,
      currency: builder.currency,
      lookback_days: params.lookbackDays,
      return_method: params.returnMethod,
      portfolio_value: builder.portfolioValue,
      var_method: params.varMethod,
      horizon_days: params.horizonDays,
      fx_mode: builder.fxMode,
    });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <MarketHeader
        refreshing={universe.refreshing}
        onAudit={() => universe.refresh(false)}
        onLiveRefresh={() => universe.refresh(true)}
      />

      {universe.refreshNotice && <Alert tone={universe.refreshNotice.tone}>{universe.refreshNotice.text}</Alert>}

      {analysis.error && (
        <Alert
          tone="error"
          title="Validation or calculation error"
          action={
            <button type="button" onClick={runAnalysis} className="text-[11px] font-semibold underline shrink-0">
              Retry
            </button>
          }
        >
          {analysis.error}
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 space-y-6 min-w-0">
          <PortfolioForm builder={builder} params={params} loading={analysis.loading} onRun={runAnalysis} />
          <UniverseCard
            symbols={universe.symbols}
            loading={universe.loading}
            loadError={universe.loadError}
            onRetry={universe.reload}
            onAdd={(symbol) => builder.addAsset({ symbol })}
          />
        </div>

        <div className="lg:col-span-7 min-w-0">
          <ResultsPanel
            metrics={analysis.metrics}
            loading={analysis.loading}
            stressResults={analysis.stressResults}
            stressLoading={analysis.stressLoading}
            stressError={analysis.stressError}
            stressInput={stressInput}
          />
        </div>
      </div>
    </div>
  );
}
