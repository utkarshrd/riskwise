"use client";

import { useCallback, useState } from "react";
import { api, type FxMode, type VaRValidationResponse } from "@/lib/api";

export interface ValidationRequest {
  holdings: Array<{ symbol: string; weight?: number }>;
  portfolio_name: string;
  currency: string;
  method: string;
  confidence_level: number;
  lookback_window: number;
  fx_mode: FxMode;
}

/** Runs one rolling VaR backtest and tracks its loading and error state. */
export function useValidationRun(onCompleted: () => void) {
  const [result, setResult] = useState<VaRValidationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (req: ValidationRequest) => {
      setLoading(true);
      setError(null);
      try {
        setResult(await api.market.validateVar(req));
        onCompleted();
      } catch (err) {
        setError(err instanceof Error ? err.message : "VaR validation failed.");
      } finally {
        setLoading(false);
      }
    },
    [onCompleted]
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, loading, error, setError, run, reset };
}
