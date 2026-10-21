import Link from "next/link";
import { 
  CreditCard, 
  Activity, 
  TrendingUp, 
  CheckCircle2, 
  Bot, 
  Server, 
  AlertTriangle,
  ArrowRight,
  Database,
  Info
} from "lucide-react";

const modules = [
  {
    id: "M1-M2",
    title: "Credit Risk Intelligence & SHAP",
    description: "Multi-model credit default classifier, local & global SHAP explainability, and constrained what-if counterfactual exploration.",
    href: "/credit",
    icon: CreditCard,
    status: "Pending M1 Training",
    statusColor: "text-amber-600 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800",
    provenance: "Indian Banking & CIBIL Bureau Dataset",
    actionText: "Configure Data Pipeline",
  },
  {
    id: "M3",
    title: "Personal Financial Stress & Affordability",
    description: "Deterministic loan EMI schedules, EMI-to-income ratio analysis, emergency cash-flow runway, and adverse shock scenarios.",
    href: "/stress",
    icon: Activity,
    status: "Pending M3 Engine",
    statusColor: "text-slate-600 bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800",
    provenance: "Deterministic mathematical formulas",
    actionText: "View Calculation Models",
  },
  {
    id: "M4",
    title: "Portfolio Market Risk Lab",
    description: "Historical and Parametric Value-at-Risk (VaR), Expected Shortfall (CVaR), peak-to-trough drawdowns, and historical market stress testing.",
    href: "/market-risk",
    icon: TrendingUp,
    status: "Pending M4 Snapshot",
    statusColor: "text-amber-600 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800",
    provenance: "Local daily price snapshots (data/market_snapshots/)",
    actionText: "Inspect Market Universe",
  },
  {
    id: "M5",
    title: "Rolling VaR Model Validation",
    description: "Rolling out-of-sample backtesting against subsequent realized portfolio losses. Strict temporal separation with zero look-ahead bias.",
    href: "/var-validation",
    icon: CheckCircle2,
    status: "Pending M5 Protocol",
    statusColor: "text-slate-600 bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800",
    provenance: "Trailing lookback window evaluation",
    actionText: "Review Validation Method",
  },
  {
    id: "M6",
    title: "Agentic Risk Copilot",
    description: "Bounded LangGraph workflow orchestrating verified domain calculation tools and source-grounded RAG retrieval with citations.",
    href: "/copilot",
    icon: Bot,
    status: "Pending M6 Graph",
    statusColor: "text-blue-600 bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800",
    provenance: "Curated knowledge corpus (knowledge/manifest.csv)",
    actionText: "Test Offline Copilot",
  },
  {
    id: "M7",
    title: "ML Monitoring & Model Registry",
    description: "Model artifact lineage, evaluation metadata comparison, Population Stability Index (PSI) drift tracking, and gated challenger promotions.",
    href: "/model-health",
    icon: Server,
    status: "Pending M7 Registry",
    statusColor: "text-slate-600 bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800",
    provenance: "SQLite registry & immutable artifact storage",
    actionText: "Inspect Registry",
  },
];

export default function OverviewPage() {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header section */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          RiskWise Intelligence Dashboard
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Milestone 0 Architectural Wireframe & Verification Baseline
        </p>
      </div>

      {/* Provenance & Offline Disclosures Banner */}
      <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl p-4 sm:p-5 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-semibold text-amber-900 dark:text-amber-200">
              Zero-Budget / Offline-First Compliance Notice
            </p>
            <p className="text-amber-800 dark:text-amber-300 leading-relaxed">
              All metrics are computed exclusively from local data snapshots and deterministic formulas. No paid APIs, cloud data warehouses, or external LLM credentials are required for platform operation.
            </p>
          </div>
        </div>
        <Link
          href="/methodology"
          className="shrink-0 text-xs font-medium text-amber-900 dark:text-amber-200 bg-amber-100 dark:bg-amber-900/60 hover:bg-amber-200 px-3 py-1.5 rounded-lg border border-amber-300 dark:border-amber-700 transition"
        >
          View Methodology Disclosures
        </Link>
      </div>

      {/* System Baseline Status Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-xs font-medium mb-1">
            <Info className="w-4 h-4 text-indigo-500" />
            <span>Architecture Style</span>
          </div>
          <div className="text-lg font-bold text-slate-900 dark:text-slate-100">Modular Monolith</div>
          <div className="text-xs text-slate-500 mt-1">FastAPI + Next.js App Router</div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-xs font-medium mb-1">
            <Database className="w-4 h-4 text-emerald-500" />
            <span>Active Milestone</span>
          </div>
          <div className="text-lg font-bold text-slate-900 dark:text-slate-100">Milestone 0 (Setup)</div>
          <div className="text-xs text-emerald-600 dark:text-emerald-400 font-medium mt-1">Foundations Complete</div>
        </div>

        <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-xs font-medium mb-1">
            <Server className="w-4 h-4 text-blue-500" />
            <span>Anti-Fabrication Guard</span>
          </div>
          <div className="text-lg font-bold text-slate-900 dark:text-slate-100">Strict Enforcement</div>
          <div className="text-xs text-slate-500 mt-1">Zero placeholder/mock chart data</div>
        </div>
      </div>

      {/* Modules Wireframe Grid */}
      <div>
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Core Domain Modules
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {modules.map((mod) => {
            const Icon = mod.icon;
            return (
              <div
                key={mod.id}
                className="flex flex-col justify-between p-5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700 transition"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="p-2.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${mod.statusColor}`}>
                      {mod.status}
                    </span>
                  </div>

                  <h3 className="font-semibold text-sm text-slate-900 dark:text-slate-100 mb-1">
                    {mod.title}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-4">
                    {mod.description}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
                  <div className="text-[11px] text-slate-400 mb-3 truncate">
                    <span className="font-medium text-slate-500 dark:text-slate-300">Source:</span> {mod.provenance}
                  </div>
                  <Link
                    href={mod.href}
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    <span>{mod.actionText}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
