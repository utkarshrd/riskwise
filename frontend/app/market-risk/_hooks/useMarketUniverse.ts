"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Cached-symbol list plus the snapshot audit / live refresh actions. */
export function useMarketUniverse() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshNotice, setRefreshNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const u = await api.market.universe();
      setSymbols(u.supported_symbols || []);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Could not load the cached symbol list.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.market
      .universe()
      .then((u) => {
        if (!cancelled) setSymbols(u.supported_symbols || []);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(err instanceof Error ? err.message : "Could not load the cached symbol list.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refresh = useCallback(
    async (live: boolean) => {
      setRefreshing(true);
      setRefreshNotice(null);
      try {
        const res = await api.market.refresh({ fetch_live: live });
        setRefreshNotice({
          tone: "success",
          text:
            live && res.data_source_mode === "live_refreshed"
              ? `Live refresh successful via Yahoo Finance (${res.refreshed_at.slice(0, 19)}Z).`
              : `Snapshot audited successfully (${res.supported_symbols.length} tickers verified). Mode: ${res.data_source_mode}.`,
        });
        await load();
      } catch (err) {
        setRefreshNotice({ tone: "error", text: err instanceof Error ? `Refresh failed: ${err.message}` : "Refresh failed." });
      } finally {
        setRefreshing(false);
      }
    },
    [load]
  );

  const addSymbol = useCallback((symbol: string) => {
    setSymbols((prev) => (prev.includes(symbol) ? prev : [...prev, symbol].sort()));
  }, []);

  return { symbols, loading, loadError, reload: load, refreshing, refreshNotice, refresh, addSymbol };
}
