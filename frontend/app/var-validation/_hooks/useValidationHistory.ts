"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type VaRValidationHistoryItem } from "@/lib/api";

/** The most recent persisted validation runs. `reload` is safe to call after each new run. */
export function useValidationHistory(limit = 10) {
  const [runs, setRuns] = useState<VaRValidationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.market
      .history(limit)
      .then((h) => !cancelled && setRuns(h))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Could not load run history."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [limit]);

  const reload = useCallback(async () => {
    try {
      setRuns(await api.market.history(limit));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load run history.");
    }
  }, [limit]);

  return { runs, loading, error, reload };
}
