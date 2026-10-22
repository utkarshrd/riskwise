import type { ReactNode } from "react";

export const inputClass =
  "w-full text-xs px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500";

interface FieldProps {
  label: ReactNode;
  htmlFor: string;
  children: ReactNode;
  hint?: ReactNode;
  className?: string;
}

/** Label + control pair. The control must carry the matching id. */
export function Field({ label, htmlFor, children, hint, className = "" }: FieldProps) {
  return (
    <div className={`space-y-1 min-w-0 ${className}`}>
      <label htmlFor={htmlFor} className="flex items-center gap-1 text-xs font-medium text-slate-700 dark:text-slate-300">
        {label}
      </label>
      {children}
      {hint && <p className="text-[10px] text-slate-400">{hint}</p>}
    </div>
  );
}
