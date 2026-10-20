import Link from "next/link";
import { 
  ShieldAlert, 
  CreditCard, 
  Activity, 
  Calculator, 
  TrendingUp, 
  CheckCircle2, 
  Bot, 
  Server, 
  BookOpen,
  LayoutDashboard
} from "lucide-react";

export const navigationLinks = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/credit", label: "Credit Risk & SHAP", icon: CreditCard, milestone: "M1-M2" },
  { href: "/stress", label: "Financial Stress", icon: Activity, milestone: "M3" },
  { href: "/loans", label: "Loan Affordability", icon: Calculator, milestone: "M3" },
  { href: "/market-risk", label: "Market Risk Lab", icon: TrendingUp, milestone: "M4" },
  { href: "/var-validation", label: "VaR Validation", icon: CheckCircle2, milestone: "M5" },
  { href: "/copilot", label: "Risk Copilot", icon: Bot, milestone: "M6" },
  { href: "/model-health", label: "Model Registry & Drift", icon: Server, milestone: "M7" },
  { href: "/methodology", label: "Methodology & Disclosures", icon: BookOpen, milestone: "M0" },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col border-r border-slate-800 shrink-0 min-h-screen">
      <div className="p-5 border-b border-slate-800 flex items-center gap-3">
        <div className="p-2 bg-indigo-600 rounded-lg text-white">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <div>
          <h1 className="font-bold text-lg text-white tracking-tight">RiskWise</h1>
          <p className="text-xs text-slate-400">Financial Risk Intelligence</p>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-3 py-2">
          Platform Modules
        </div>
        {navigationLinks.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4 text-slate-400" />
                <span>{item.label}</span>
              </div>
              {item.milestone && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {item.milestone}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 text-xs text-slate-400 bg-slate-950/40">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="font-medium text-slate-300">Offline-Ready Mode</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          Zero external API dependencies required. PRD v3.0 Milestone 0 baseline.
        </p>
      </div>
    </aside>
  );
}
