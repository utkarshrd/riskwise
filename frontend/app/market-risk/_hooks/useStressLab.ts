"use client";

import { useCallback, useState } from "react";
import { api, type ReverseStressResult, type StressInput, type StressReplayScenario } from "@/lib/api";

/** On-demand named-event replays and reverse stress for the portfolio behind the current results. */
export function useStressLab(input: StressInput | null) {
  const [replays, setReplays] = useState<StressReplayScenario[] | null>(null);
  const [replayLoading, setReplayLoading] = useState(false);
  const [replayError, setReplayError] = useState<string | null>(null);

  const [reverse, setReverse] = useState<ReverseStressResult | null>(null);
  const [reverseLoading, setReverseLoading] = useState(false);
  const [reverseError, setReverseError] = useState<string | null>(null);

  const runReplay = useCallback(async () => {
    if (!input) return;
    setReplayLoading(true);
    setReplayError(null);
    try {
      setReplays(await api.market.stressReplay(input));
    } catch (err) {
      setReplays(null);
      setReplayError(err instanceof Error ? err.message : "The historical replay failed.");
    } finally {
      setReplayLoading(false);
    }
  }, [input]);

  const runReverse = useCallback(
    async (target: { target_loss_pct?: number; target_loss_amount?: number }) => {
      if (!input) return;
      setReverseLoading(true);
      setReverseError(null);
      try {
        setReverse(await api.market.stressReverse(input, target));
      } catch (err) {
        setReverse(null);
        setReverseError(err instanceof Error ? err.message : "The reverse stress test failed.");
      } finally {
        setReverseLoading(false);
      }
    },
    [input]
  );

  return { replays, replayLoading, replayError, runReplay, reverse, reverseLoading, reverseError, runReverse };
}
