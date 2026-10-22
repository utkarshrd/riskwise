"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  Bot,
  CheckCircle2,
  CreditCard,
  Server,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { Alert, Badge, Card, Skeleton, type Tone } from "@/components/ui";
import { api, type SystemStatus } from "@/lib/api";

interface ModuleCard {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  source: string;
  cta: string;
  /** Live status chip derived from the system status endpoint; null while it is unavailable. */
  status: (s: SystemStatus) => { label: string; tone: Tone };
}

const MODULES: ModuleCard[] = [
  {
    title: "Credit Risk Intelligence & SHAP",
    description:
      "Four-tier credit risk classification for Indian borrowers with SHAP explanations and a what-if lab. The bureau Credit Score is deliberately not an input.",
    href: "/credit",
    icon: CreditCard,
    source: "Indian banking and CIBIL bureau dataset (51,336 records)",
    cta: "Score a borrower profile",
    status: (s) =>
      s.credit_model_loaded
        ? { label: `Model ${s.active_model_version ?? "loaded"}`, tone: "green" }
        : { label: "Model not loaded", tone: "red" },
  },
  {
    title: "Personal Financial Stress & Affordability",
    description: "EMI schedules, EMI-to-income ratio, emergency runway and adverse income or expense shocks, all from closed-form formulas.",
    href: "/stress",
    icon: Activity,
    source: "Deterministic formulas, no model involved",
    cta: "Stress-test a household budget",
    status: () => ({ label: "Deterministic", tone: "indigo" }),
  },
  {
    title: "Portfolio Market Risk Lab",
    description:
      "VaR by eight methods, expected shortfall, drawdown, correlation, named historical stress replays, reverse stress and CSV import for NSE and US portfolios.",
    href: "/market-risk",
    icon: TrendingUp,
    source: "Local price snapshots, with live Yahoo Finance fetches for new symbols",
    cta: "Analyse a portfolio",
    status: (s) =>
      s.market_snapshot_loaded
        ? { label: `${s.market_tickers_available.length} symbols cached`, tone: "green" }
        : { label: "No snapshots", tone: "amber" },
  },
  {
    title: "Rolling VaR Model Validation",
    description: "Out-of-sample backtests with the Kupiec and Christoffersen tests and the Basel traffic light, plus a side-by-side model comparison.",
    href: "/var-validation",
    icon: CheckCircle2,
    source: "Trailing-window forecasts, no look-ahead",
    cta: "Backtest a VaR model",
    status: () => ({ label: "Deterministic", tone: "indigo" }),
  },
  {
    title: "Risk Copilot",
    description:
      "Ask in plain language. The copilot calls the same calculation tools, shows its tool trace and removes any number that no tool or source produced.",
    href: "/copilot",
    icon: Bot,
    source: "Curated knowledge corpus with citations",
    cta: "Ask a question",
    status: (s) => ({ label: `${s.vector_index_chunk_count ?? 0} knowledge chunks`, tone: s.rag_corpus_loaded ? "green" : "amber" }),
  },
  {
    title: "Model Registry & Drift",
    description: "Registered model versions, evaluation metadata and population-stability drift checks.",
    href: "/model-health",
    icon: Server,
    source: "SQLite registry and stored evaluation artifacts",
    cta: "Inspect the registry",
    status: (s) => ({ label: s.active_model_version ? `Active ${s.active_model_version}` : "No active model", tone: s.active_model_version ? "green" : "amber" }),
  },
];

export default function OverviewPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.system
      .status()
      .then((s) => !cancelled && setStatus(s))
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Could not reach the API."))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">RiskWise Intelligence Dashboard</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
          Credit risk, personal finance and market risk analytics. Every figure comes from a deterministic calculation or a named dataset, never from a placeholder.
        </p>
      </div>

      {error && (
        <Alert tone="warning" title="The API is not reachable">
          {error} The module links below still work once the backend is running.
        </Alert>
      )}

      <section aria-label="Platform status" className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {loading ? (
          [0, 1, 2].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)
        ) : status ? (
          <>
            <Card>
              <div className="text-[11px] text-slate-500">Platform</div>
              <div className="text-lg font-bold capitalize text-slate-900 dark:text-slate-100">{status.status}</div>
              <div className="text-[11px] text-slate-400">Database revision {status.migration_revision ?? "unknown"}</div>
            </Card>
            <Card>
              <div className="text-[11px] text-slate-500">Market data</div>
              <div className="text-lg font-bold text-slate-900 dark:text-slate-100">{status.market_tickers_available.length} symbols cached</div>
              <div className="text-[11px] text-slate-400">
                Snapshot checksums {status.snapshot_checksum_verified ? "verified" : "not verified"}
              </div>
            </Card>
            <Card>
              <div className="text-[11px] text-slate-500">Language model</div>
              <div className="text-lg font-bold text-slate-900 dark:text-slate-100">{status.llm_provider_configured ? "Configured" : "Not used"}</div>
              <div className="text-[11px] text-slate-400">Replies are composed from tool results either way</div>
            </Card>
          </>
        ) : null}
      </section>

      <section aria-label="Modules" className="space-y-4">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Modules</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {MODULES.map((m) => {
            const Icon = m.icon;
            const chip = status ? m.status(status) : null;
            return (
              <Card key={m.href} className="flex flex-col gap-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                    <Icon className="w-5 h-5" />
                  </div>
                  {chip && <Badge tone={chip.tone}>{chip.label}</Badge>}
                </div>
                <div className="space-y-1.5 flex-1">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{m.title}</h3>
                  <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">{m.description}</p>
                </div>
                <div className="pt-3 border-t border-slate-100 dark:border-slate-800 space-y-2">
                  <p className="text-[11px] text-slate-400">
                    <span className="font-semibold text-slate-500">Source:</span> {m.source}
                  </p>
                  <Link
                    href={m.href}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    {m.cta} <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </Card>
            );
          })}
        </div>
      </section>

      <Alert tone="info" title="How to read the results">
        These tools are educational. Value at Risk describes a loss threshold, not a worst case; credit tiers are relative risk within the training dataset, not a bureau score;
        and nothing here is investment advice.{" "}
        <Link href="/methodology" className="font-semibold underline">
          Read the methodology and limitations
        </Link>
        .
      </Alert>
    </div>
  );
}
