import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  /** Set false for cards whose children (tables) should touch the border. */
  padded?: boolean;
}

export function Card({ children, className = "", padded = true }: CardProps) {
  return (
    <section
      className={`bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm min-w-0 ${
        padded ? "p-4 sm:p-5" : "overflow-hidden"
      } ${className}`}
    >
      {children}
    </section>
  );
}

interface CardHeaderProps {
  title: ReactNode;
  icon?: ReactNode;
  /** Right-aligned secondary content (badge, note, action). */
  right?: ReactNode;
  className?: string;
}

export function CardHeader({ title, icon, right, className = "" }: CardHeaderProps) {
  return (
    <div className={`flex flex-wrap items-center justify-between gap-x-3 gap-y-1 ${className}`}>
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100 min-w-0">
        {icon}
        <span className="min-w-0">{title}</span>
      </h3>
      {right && <div className="text-[11px] text-slate-500 dark:text-slate-400">{right}</div>}
    </div>
  );
}
