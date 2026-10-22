import type { ReactNode } from "react";
import { MetricInfo } from "@/components/ui/Tooltip";
import type { MetricKey } from "@/lib/metric-docs";

type StatTone = "default" | "good" | "bad" | "accent" | "warn";

const VALUE_TONES: Record<StatTone, string> = {
  default: "text-slate-900 dark:text-slate-100",
  good: "text-emerald-600 dark:text-emerald-400",
  bad: "text-red-600 dark:text-red-400",
  accent: "text-indigo-600 dark:text-indigo-400",
  warn: "text-amber-600 dark:text-amber-400",
};

interface StatProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: StatTone;
  /** Adds an (i) tooltip that links to the metric's methodology section. */
  metric?: MetricKey;
}

export function Stat({ label, value, hint, tone = "default", metric }: StatProps) {
  return (
    <div className="p-3.5 sm:p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-1 min-w-0">
      <div className="flex items-center gap-1 text-[11px] font-medium text-slate-500 dark:text-slate-400">
        <span className="min-w-0">{label}</span>
        {metric && <MetricInfo metric={metric} />}
      </div>
      <div className={`text-lg font-bold font-mono truncate ${VALUE_TONES[tone]}`}>{value}</div>
      {hint && <div className="text-[10px] text-slate-400">{hint}</div>}
    </div>
  );
}
