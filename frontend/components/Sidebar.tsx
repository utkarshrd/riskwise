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
  { href: "/credit", label: "Credit Risk & SHAP", icon: CreditCard },
  { href: "/stress", label: "Financial Stress", icon: Activity },
  { href: "/loans", label: "Loan Affordability", icon: Calculator },
  { href: "/market-risk", label: "Market Risk Lab", icon: TrendingUp },
  { href: "/var-validation", label: "VaR Validation", icon: CheckCircle2 },
  { href: "/copilot", label: "Risk Copilot", icon: Bot },
  { href: "/model-health", label: "Model Registry & Drift", icon: Server },
  { href: "/methodology", label: "Methodology & Disclosures", icon: BookOpen },
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
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800 text-xs text-slate-400 bg-slate-950/40">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span className="font-medium text-slate-300">Quantitative Risk Engine</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          Institutional analytics with deterministic calculations and real NSE market coverage.
        </p>
      </div>
    </aside>
  );
}
