import { Server, Activity, ShieldAlert } from "lucide-react";

export default function ModelHealthPage() {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500 mb-1">
          <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
            Milestone 7 Deliverable
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Model Registry & Drift Monitoring
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Model lineage tracking, Population Stability Index (PSI) feature drift computation, and gated challenger promotion.
        </p>
      </div>

      <div className="p-6 rounded-xl border border-dashed border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 text-center space-y-4">
        <div className="inline-flex p-3 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">
          <Server className="w-8 h-8" />
        </div>
        <div className="max-w-md mx-auto space-y-2">
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Model Registry Empty (Uninitialized State)
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            No active models are registered yet. Registry entries, version checksums, PSI drift metrics, and champion/challenger comparison protocols will be activated during model training and evaluation milestones.
          </p>
        </div>

        <div className="flex justify-center gap-4 pt-2">
          <div className="inline-flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700">
            <Activity className="w-4 h-4 text-amber-500" />
            <span>PSI Drift Tracking</span>
          </div>
          <div className="inline-flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/60 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700">
            <ShieldAlert className="w-4 h-4 text-indigo-500" />
            <span>Gated Challenger Promotion</span>
          </div>
        </div>
      </div>
    </div>
  );
}
