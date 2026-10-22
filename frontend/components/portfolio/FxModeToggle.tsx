import type { FxMode } from "@/lib/api";

interface FxModeToggleProps {
  value: FxMode;
  onChange: (mode: FxMode) => void;
  baseCurrency: string;
}

export default function FxModeToggle({ value, onChange, baseCurrency }: FxModeToggleProps) {
  const on = value === "convert_to_base";
  return (
    <label className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/40 cursor-pointer">
      <input
        type="checkbox"
        checked={on}
        onChange={(e) => onChange(e.target.checked ? "convert_to_base" : "strict")}
        className="mt-0.5 accent-indigo-600"
      />
      <span className="text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
        <span className="block text-xs font-medium text-slate-800 dark:text-slate-200">Allow mixed USD and INR holdings</span>
        Convert everything into {baseCurrency} using daily USD/INR history. Off by default: portfolios stay single-currency.
      </span>
    </label>
  );
}
