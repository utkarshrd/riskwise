"use client";

import { Menu } from "lucide-react";
import ThemeToggle from "@/components/shell/ThemeToggle";

export default function Header({ onMenuClick }: { onMenuClick: () => void }) {
  return (
    <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 sm:px-6 flex items-center justify-between gap-3 sticky top-0 z-20">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Open navigation"
          className="p-2 -ml-1 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2 text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 whitespace-nowrap">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          <span className="hidden min-[420px]:inline">System Status:&nbsp;</span>Operational
        </div>
        <div className="text-xs text-slate-500 dark:text-slate-400 hidden xl:block truncate">
          Backend API: <code className="bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-700 dark:text-slate-300 font-mono">http://localhost:8000/api/v1</code>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 shrink-0">
        <span className="hidden md:inline">SQLite / Local Cache</span>
        <span className="hidden lg:inline">Deterministic Engines</span>
        <ThemeToggle />
      </div>
    </header>
  );
}
