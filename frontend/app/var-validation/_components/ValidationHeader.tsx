import { ShieldAlert } from "lucide-react";


export default function ValidationHeader() {
  return (
    <>
      <div className="border-b border-slate-200 dark:border-slate-800 pb-5">
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400 mb-1 tracking-wide uppercase">
          <span className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800">
            Regulatory Model Validation
          </span>
          <span className="text-slate-400">•</span>
          <span>Out-of-Sample Backtesting</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Rolling VaR Model Validation & Backtesting</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-3xl">
          Checks whether a VaR model&apos;s forecasts held up against the losses that actually followed. Includes the Kupiec test, the Christoffersen tests and the Basel traffic-light classification.
        </p>
      </div>

      <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/30 text-amber-950 dark:text-amber-200 text-xs flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-semibold text-sm">Regulatory VaR forecast validation, not trading-strategy backtesting</div>
          <p className="leading-relaxed text-[11px] text-amber-900 dark:text-amber-300">
            At each day <code>t</code> the model is estimated only from the preceding window <code>[t-W, t)</code> and then compared with the loss on day <code>t</code>, so no future data is used. This does not simulate rebalancing or trading returns.
          </p>
        </div>
      </div>
    </>
  );
}
