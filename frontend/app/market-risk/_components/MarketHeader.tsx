import { RefreshCw } from "lucide-react";

interface MarketHeaderProps {
  refreshing: boolean;
  onAudit: () => void;
  onLiveRefresh: () => void;
}

export default function MarketHeader({ refreshing, onAudit, onLiveRefresh }: MarketHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-indigo-600 dark:text-indigo-400 mb-1 tracking-wide uppercase">
          <span className="px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800">
            Quantitative Market Risk
          </span>
          <span className="text-slate-400">•</span>
          <span>Single-Currency Portfolios</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Portfolio Market Risk Lab</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
          Value at Risk (historical, Gaussian and six other methods), Expected Shortfall, volatility, drawdown, correlation and historical stress tests for NSE and US portfolios.
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={onAudit}
          disabled={refreshing}
          title="Verify local CSV price snapshots and manifest checksums"
          className="px-3 py-2 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 flex items-center gap-1.5 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          Audit Snapshots
        </button>
        <button
          type="button"
          onClick={onLiveRefresh}
          disabled={refreshing}
          title="Attempt live price update from Yahoo Finance"
          className="px-3 py-2 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
          Live Yahoo Refresh
        </button>
      </div>
    </div>
  );
}
