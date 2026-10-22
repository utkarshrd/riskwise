"use client";

import { useState } from "react";
import WaterfallChart from "@/components/WaterfallChart";
import { Alert, Field, inputClass, MetricInfo, Skeleton, Tabs } from "@/components/ui";
import type { ReverseStressResult } from "@/lib/api";
import { formatCurrency, formatPct } from "@/lib/format";

interface ReverseStressProps {
  result: ReverseStressResult | null;
  loading: boolean;
  error: string | null;
  currency: string;
  portfolioValue?: number;
  onRun: (target: { target_loss_pct?: number; target_loss_amount?: number }) => void;
}

type View = "uniform" | "beta";

export default function ReverseStress({ result, loading, error, currency, portfolioValue, onRun }: ReverseStressProps) {
  const [mode, setMode] = useState<"pct" | "amount">("pct");
  const [pct, setPct] = useState(20);
  const [amount, setAmount] = useState(Math.round((portfolioValue ?? 100000) * 0.2));
  const [view, setView] = useState<View>("uniform");

  const submit = () => onRun(mode === "pct" ? { target_loss_pct: pct / 100 } : { target_loss_amount: amount });
  const canRun = mode === "pct" ? pct > 0 && pct < 100 : amount > 0 && !!portfolioValue && amount < portfolioValue;

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
        Start from a loss you could not accept and work backwards: how far would the market have to fall to cause it? <MetricInfo metric="reverse_stress" />
      </p>

      <div className="flex flex-wrap items-end gap-3">
        <Tabs
          ariaLabel="Target loss as"
          value={mode}
          onChange={setMode}
          tabs={[
            { id: "pct", label: "% of portfolio" },
            { id: "amount", label: `Amount (${currency})` },
          ]}
        />
        {mode === "pct" ? (
          <Field label="Loss I want to test (%)" htmlFor="rs-pct" className="w-40">
            <input id="rs-pct" type="number" min={1} max={99} step={1} value={pct} onChange={(e) => setPct(Number(e.target.value))} className={`${inputClass} font-mono`} />
          </Field>
        ) : (
          <Field label={`Loss I want to test (${currency})`} htmlFor="rs-amt" className="w-48">
            <input id="rs-amt" type="number" min={1} step={1000} value={amount} onChange={(e) => setAmount(Number(e.target.value))} className={`${inputClass} font-mono`} />
          </Field>
        )}
        <button
          type="button"
          onClick={submit}
          disabled={loading || !canRun}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold disabled:opacity-50"
        >
          {loading ? "Working it out…" : "Find the shock"}
        </button>
      </div>
      {mode === "amount" && !portfolioValue && <Alert tone="warning">Enter a portfolio value in the setup to test a loss amount.</Alert>}
      {error && <Alert tone="error">{error}</Alert>}

      {loading && <Skeleton className="h-56" />}

      {result && !loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40">
              <div className="text-[11px] text-slate-500">Every holding falls by</div>
              <div className="text-2xl font-bold font-mono text-red-600 dark:text-red-400">{formatPct(Math.abs(result.uniform_asset_shock))}</div>
              <div className="text-[11px] text-slate-400">
                = a {formatPct(result.target_loss_pct)} portfolio loss
                {result.target_loss_amount != null && ` (${formatCurrency(result.target_loss_amount, result.currency)})`}
              </div>
            </div>
            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40">
              <div className="text-[11px] text-slate-500">Or {result.benchmark_symbol} falls by</div>
              {result.implied_benchmark_shock != null ? (
                <div className="text-2xl font-bold font-mono text-red-600 dark:text-red-400">{formatPct(Math.abs(result.implied_benchmark_shock))}</div>
              ) : (
                <div className="text-2xl font-bold font-mono text-slate-400">N/A</div>
              )}
              <div className="text-[11px] text-slate-400">
                at portfolio beta {result.portfolio_beta.toFixed(2)}, from {result.lookback_observations} days ({result.lookback_start} to {result.lookback_end})
              </div>
            </div>
          </div>

          {result.note && <Alert tone="warning">{result.note}</Alert>}

          <div className="space-y-2">
            <Tabs
              ariaLabel="Reverse stress breakdown"
              value={view}
              onChange={setView}
              tabs={[
                { id: "uniform", label: "Uniform shock" },
                ...(result.beta_contributions.length > 0 ? [{ id: "beta" as const, label: `${result.benchmark_symbol} shock at each beta` }] : []),
              ]}
            />
            <WaterfallChart
              items={(view === "beta" ? result.beta_contributions : result.uniform_contributions).map((c) => ({
                label: c.symbol.replace(".NS", ""),
                value: c.contribution,
              }))}
            />
            <p className="text-[11px] text-slate-400">
              {view === "beta"
                ? "Each holding moves by its beta times the benchmark fall, so higher-beta holdings take more of the loss."
                : "Every holding falls by the same percentage, so each one contributes in proportion to its weight."}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
