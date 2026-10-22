"use client";

import { useState } from "react";
import { Alert } from "@/components/ui";
import { usePortfolioBuilder } from "@/hooks/usePortfolioBuilder";
import BacktestForm from "./_components/BacktestForm";
import ResultsPanel from "./_components/ResultsPanel";
import RunHistory from "./_components/RunHistory";
import ValidationHeader from "./_components/ValidationHeader";
import { useValidationHistory } from "./_hooks/useValidationHistory";
import { useValidationRun } from "./_hooks/useValidationRun";
import { DEFAULT_PRESET, PRESET_PORTFOLIOS } from "./_lib/options";

export default function VaRValidationPage() {
  const [method, setMethod] = useState("historical");
  const [confidenceLevel, setConfidenceLevel] = useState(0.95);
  const [lookbackWindow, setLookbackWindow] = useState(100);

  const history = useValidationHistory(10);
  const validation = useValidationRun(history.reload);

  const builder = usePortfolioBuilder({
    presets: PRESET_PORTFOLIOS,
    defaultPreset: DEFAULT_PRESET,
    onProblem: validation.setError,
    onPortfolioReset: validation.reset,
  });

  const runValidation = () =>
    validation.run({
      holdings: builder.holdings.map((h) => ({ symbol: h.symbol, weight: Number(h.weight) })),
      portfolio_name: builder.portfolioName,
      currency: builder.currency,
      method,
      confidence_level: confidenceLevel,
      lookback_window: lookbackWindow,
      fx_mode: builder.fxMode,
    });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      <ValidationHeader />

      {validation.error && (
        <Alert
          tone="error"
          title="Validation error"
          action={
            <button type="button" onClick={runValidation} className="text-[11px] font-semibold underline shrink-0">
              Retry
            </button>
          }
        >
          {validation.error}
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 space-y-6 min-w-0">
          <BacktestForm
            builder={builder}
            method={method}
            onMethodChange={setMethod}
            confidenceLevel={confidenceLevel}
            onConfidenceChange={setConfidenceLevel}
            lookbackWindow={lookbackWindow}
            onWindowChange={setLookbackWindow}
            loading={validation.loading}
            onRun={runValidation}
          />
          <RunHistory runs={history.runs} loading={history.loading} error={history.error} />
        </div>

        <div className="lg:col-span-7 min-w-0">
          <ResultsPanel
            result={validation.result}
            loading={validation.loading}
            holdings={builder.holdings.map((h) => ({ symbol: h.symbol, weight: h.weight }))}
            currency={builder.currency}
            confidenceLevel={confidenceLevel}
            lookbackWindow={lookbackWindow}
            fxMode={builder.fxMode}
            method={method}
            onSelectMethod={setMethod}
          />
        </div>
      </div>
    </div>
  );
}
