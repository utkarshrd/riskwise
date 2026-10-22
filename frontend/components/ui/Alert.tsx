import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info } from "lucide-react";

type AlertTone = "error" | "info" | "success" | "warning";

const STYLES: Record<AlertTone, { box: string; icon: string }> = {
  error: {
    box: "border-red-200 dark:border-red-900/60 bg-red-50/80 dark:bg-red-950/40 text-red-900 dark:text-red-300",
    icon: "text-red-600 dark:text-red-400",
  },
  warning: {
    box: "border-amber-200 dark:border-amber-900/60 bg-amber-50/80 dark:bg-amber-950/40 text-amber-900 dark:text-amber-300",
    icon: "text-amber-600 dark:text-amber-400",
  },
  info: {
    box: "border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200",
    icon: "text-indigo-600 dark:text-indigo-400",
  },
  success: {
    box: "border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200",
    icon: "text-emerald-600 dark:text-emerald-400",
  },
};

interface AlertProps {
  tone: AlertTone;
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}

export function Alert({ tone, title, children, action }: AlertProps) {
  const Icon = tone === "error" || tone === "warning" ? AlertTriangle : tone === "success" ? CheckCircle2 : Info;
  const s = STYLES[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`p-3.5 rounded-xl border text-xs flex items-start gap-3 ${s.box}`}
    >
      <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${s.icon}`} />
      <div className="min-w-0 flex-1 space-y-0.5 leading-relaxed">
        {title && <div className="font-semibold text-sm">{title}</div>}
        <div>{children}</div>
      </div>
      {action}
    </div>
  );
}
