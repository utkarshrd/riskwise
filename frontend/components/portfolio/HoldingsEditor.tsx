import { Trash2 } from "lucide-react";
import { Badge, type Tone } from "@/components/ui";
import { formatCurrency } from "@/lib/format";
import { inferSymbolCurrency, type HoldingRow, type InputMode, type SymbolState } from "@/lib/portfolio";

const STATE_BADGES: Record<SymbolState, { label: string; tone: Tone; pulse?: boolean }> = {
  validating: { label: "Validating…", tone: "amber", pulse: true },
  live_validated: { label: "Live Validated", tone: "purple" },
  verified_snapshot: { label: "Local Snapshot", tone: "green" },
  not_available: { label: "Unavailable", tone: "red" },
};

const fieldClass =
  "w-full text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500";

interface HoldingsEditorProps {
  holdings: HoldingRow[];
  currency: string;
  portfolioValue: number;
  inputMode: InputMode;
  totalWeight: number;
  totalPositionValue: number;
  /** Show the monetary amount next to each weight. Off for pages that only use weights. */
  showAmounts?: boolean;
  onChange: (index: number, field: "symbol" | "weight" | "position_value", value: string | number) => void;
  onRemove: (index: number) => void;
  onNormalize: () => void;
}

export default function HoldingsEditor({
  holdings,
  currency,
  portfolioValue,
  inputMode,
  totalWeight,
  totalPositionValue,
  showAmounts = true,
  onChange,
  onRemove,
  onNormalize,
}: HoldingsEditorProps) {
  const balanced = Math.abs(totalWeight - 1.0) < 0.001;

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center text-xs font-medium text-slate-700 dark:text-slate-300">
        <span>Holdings Allocation ({holdings.length} Assets)</span>
        <span
          className={`text-[11px] font-mono font-semibold ${
            balanced ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"
          }`}
        >
          Sum: {(totalWeight * 100).toFixed(1)}%
        </span>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {holdings.map((h, idx) => {
          const assetCurrency = h.currency || inferSymbolCurrency(h.symbol, currency);
          const badge = h.state ? STATE_BADGES[h.state] : null;
          return (
            <div
              key={idx}
              className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-1.5"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 min-w-0 flex-wrap">
                  <input
                    type="text"
                    aria-label={`Symbol for holding ${idx + 1}`}
                    value={h.symbol}
                    onChange={(e) => onChange(idx, "symbol", e.target.value)}
                    className="w-28 sm:w-32 text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-mono uppercase font-bold focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <Badge tone={assetCurrency === "INR" ? "green" : "blue"} className="font-mono">
                    {assetCurrency}
                  </Badge>
                  {badge && (
                    <Badge
                      tone={badge.tone}
                      className={badge.pulse ? "animate-pulse" : ""}
                      title={h.observations_count ? `${h.observations_count} observations retrieved` : undefined}
                    >
                      {badge.label}
                    </Badge>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => onRemove(idx)}
                  disabled={holdings.length <= 1}
                  aria-label={`Remove ${h.symbol}`}
                  className="p-1 text-slate-400 hover:text-red-500 transition-colors disabled:opacity-30 shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {(h.name || h.alias_note) && (
                <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate pl-0.5">
                  {h.alias_note ? (
                    <span className="text-amber-600 dark:text-amber-400 font-medium">{h.alias_note}</span>
                  ) : (
                    h.name
                  )}
                </div>
              )}

              <div className="pt-0.5">
                {inputMode === "weight" ? (
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      aria-label={`Weight of ${h.symbol} in percent`}
                      step="5"
                      min="1"
                      max="100"
                      value={Number((h.weight * 100).toFixed(2))}
                      onChange={(e) => onChange(idx, "weight", Number(e.target.value) / 100)}
                      className={fieldClass}
                    />
                    <span className="text-[11px] text-slate-400 font-mono">%</span>
                    {showAmounts && (
                      <span className="text-[10px] text-slate-400 font-mono shrink-0 min-w-16 text-right">
                        {formatCurrency(h.weight * portfolioValue, currency)}
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      aria-label={`Position value of ${h.symbol}`}
                      step="5000"
                      min="100"
                      value={h.position_value || 0}
                      onChange={(e) => onChange(idx, "position_value", e.target.value)}
                      className={fieldClass}
                    />
                    <span className="text-[10px] text-slate-400 font-mono shrink-0 w-12 text-right">
                      {totalPositionValue > 0 ? `${(((h.position_value || 0) / totalPositionValue) * 100).toFixed(1)}%` : "0%"}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {!balanced && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onNormalize}
            className="text-[11px] px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/60 border border-amber-200 dark:border-amber-800 font-medium transition-colors"
          >
            Normalize to 100%
          </button>
        </div>
      )}
    </div>
  );
}
