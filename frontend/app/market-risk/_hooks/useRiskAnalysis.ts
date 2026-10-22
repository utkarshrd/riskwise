"use client";

import { useCallback, useState } from "react";
import { api, type PortfolioRiskMetrics, type StressScenarioResult } from "@/lib/api";

type Holdings = Array<{ symbol: string; weight?: number; position_value?: number }>;

export interface AnalysisRequest {
  holdings: Holdings;
  portfolio_name: string;
  currency: string;
  lookback_days: number;
  return_method: string;
  portfolio_value: number;
  var_method: string;
  horizon_days: number;
}

/** Runs the risk analysis and the historical stress tests, tracking loading and error state for each. */
export function useRiskAnalysis() {
  const [metrics, setMetrics] = useState<PortfolioRiskMetrics | null>(null);
  const [stressResults, setStressResults] = useState<StressScenarioResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [stressLoading, setStressLoading] = useState(false);
  const [stressError, setStressError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (req: AnalysisRequest) => {
    setLoading(true);
    setError(null);
    setStressError(null);
    try {
      const res = await api.market.analyze(req);
      setMetrics(res);

      setStressLoading(true);
      try {
        setStressResults(await api.market.stressTest(req.holdings));
      } catch (err) {
        setStressResults(null);
        setStressError(err instanceof Error ? err.message : "Stress tests failed.");
      } finally {
        setStressLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Portfolio analysis failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setMetrics(null);
    setStressResults(null);
    setStressError(null);
    setError(null);
  }, []);

  return { metrics, stressResults, loading, stressLoading, stressError, error, setError, run, reset };
}
