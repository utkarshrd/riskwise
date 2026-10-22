"use client";

import { useState } from "react";
import { History } from "lucide-react";
import WaterfallChart from "@/components/WaterfallChart";
import { Alert, MetricInfo, Skeleton, Tabs } from "@/components/ui";
import type { StressReplayScenario } from "@/lib/api";
import { formatCurrency, formatPct } from "@/lib/format";

interface NamedEventsProps {
  replays: StressReplayScenario[] | null;
  loading: boolean;
  error: string | null;
  onRun: () => void;
}

function Scenario({ s }: { s: StressReplayScenario }) {
  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{s.description}</p>
        <p className="text-[11px] text-slate-400 font-mono">
          {s.window_start} to {s.window_end} • {s.data_source.replace(/_/g, " ")} • prices in {s.currency}
        </p>
      </div>

      {s.status === "unavailable" ? (
        <Alert tone="warning" title="No data for any holding in this window">
          None of your holdings have prices for these dates, so there is nothing to replay.
        </Alert>
      ) : (
        <>
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
            <div>
              <div className="text-[11px] text-slate-500">Portfolio {s.portfolio_return! < 0 ? "loss" : "gain"}</div>
              <div className={`text-2xl font-bold font-mono ${s.portfolio_return! < 0 ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}`}>
                {formatPct(Math.abs(s.portfolio_return!))}
              </div>
            </div>
            {s.portfolio_loss_amount != null && (
              <div>
                <div className="text-[11px] text-slate-500">On the covered value</div>
                <div className="text-lg font-bold font-mono text-slate-800 dark:text-slate-200">{formatCurrency(Math.abs(s.portfolio_loss_amount), s.currency)}</div>
              </div>
            )}
            <div>
              <div className="text-[11px] text-slate-500">Holdings covered</div>
              <div className="text-lg font-bold font-mono text-slate-800 dark:text-slate-200">{formatPct(s.covered_weight, 0)}</div>
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-300 mb-1">What each holding contributed</div>
            <WaterfallChart items={s.contributions.map((c) => ({ label: c.symbol.replace(".NS", ""), value: c.contribution }))} />
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-100 dark:border-slate-800">
            <table className="w-full text-left text-[11px] font-mono">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-3 py-2">Holding</th>
                  <th className="px-3 py-2">From</th>
                  <th className="px-3 py-2">To</th>
                  <th className="px-3 py-2 text-right">Return</th>
                  <th className="px-3 py-2 text-right">Lowest point</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {s.contributions.map((c) => (
                  <tr key={c.symbol}>
                    <td className="px-3 py-1.5 font-semibold text-slate-800 dark:text-slate-200">{c.symbol}</td>
                    <td className="px-3 py-1.5 text-slate-500">
                      {c.start_date} @ {c.start_price.toLocaleString()}
                    </td>
                    <td className="px-3 py-1.5 text-slate-500">
                      {c.end_date} @ {c.end_price.toLocaleString()}
                    </td>
                    <td className={`px-3 py-1.5 text-right font-bold ${c.return < 0 ? "text-red-600 dark:text-red-400" : "text-emerald-600 dark:text-emerald-400"}`}>{formatPct(c.return)}</td>
                    <td className="px-3 py-1.5 text-right text-slate-500">{formatPct(c.trough_return)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {s.skipped.length > 0 && (
        <Alert tone="warning" title={`${s.skipped.length} holding${s.skipped.length === 1 ? "" : "s"} skipped`}>
          <ul className="list-disc list-inside space-y-0.5">
            {s.skipped.map((k) => (
              <li key={k.symbol}>
                <strong>{k.symbol}</strong>: {k.reason}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-[11px] opacity-80">The result covers only the holdings that had prices, re-weighted to 100% of that covered part.</p>
        </Alert>
      )}
    </div>
  );
}

export default function NamedEvents({ replays, loading, error, onRun }: NamedEventsProps) {
  const [active, setActive] = useState<string>("covid_2020");

  if (!replays && !loading) {
    return (
      <div className="space-y-3">
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          Replay real market events against these holdings: what each stock actually did between two fixed dates <MetricInfo metric="stress_replay" />. The first run for a symbol downloads its historical prices, which can take a few seconds.
        </p>
        {error && <Alert tone="error">{error}</Alert>}
        <button
          type="button"
          onClick={onRun}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold inline-flex items-center gap-2"
        >
          <History className="w-3.5 h-3.5" /> Replay COVID, election day and Adani
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-3" role="status" aria-live="polite">
        <span className="sr-only">Replaying historical events…</span>
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const current = replays!.find((r) => r.id === active) ?? replays![0];
  return (
    <div className="space-y-4">
      <Tabs ariaLabel="Historical event" value={current.id} onChange={setActive} tabs={replays!.map((r) => ({ id: r.id, label: r.name.replace(/ \(.*\)$/, "") }))} />
      <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{current.name}</h4>
      <Scenario s={current} />
    </div>
  );
}
