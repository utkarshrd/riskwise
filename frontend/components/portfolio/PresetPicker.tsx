import type { PresetMap } from "@/lib/portfolio";

interface PresetPickerProps {
  presets: PresetMap;
  selected: string;
  onSelect: (key: string) => void;
  label?: string;
  accent?: "indigo" | "emerald";
  /** Show each holding's weight next to its symbol. */
  showWeights?: boolean;
}

const ACCENTS = {
  indigo: "border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200 font-medium",
  emerald: "border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200 font-medium",
};

export default function PresetPicker({
  presets,
  selected,
  onSelect,
  label = "Presets",
  accent = "indigo",
  showWeights = false,
}: PresetPickerProps) {
  return (
    <div className="space-y-2">
      <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{label}</span>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {Object.entries(presets).map(([key, p]) => (
          <button
            key={key}
            type="button"
            onClick={() => onSelect(key)}
            aria-pressed={selected === key}
            className={`text-left p-2.5 rounded-lg border text-xs transition-all ${
              selected === key
                ? ACCENTS[accent]
                : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 text-slate-600 dark:text-slate-400"
            }`}
          >
            <div className="font-semibold text-slate-800 dark:text-slate-200 text-[11px] truncate">{p.name}</div>
            <div className="text-[10px] text-slate-400 mt-0.5 truncate">
              {p.currency} •{" "}
              {p.holdings.map((h) => (showWeights ? `${h.symbol} (${Math.round(h.weight * 100)}%)` : h.symbol)).join(", ")}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
