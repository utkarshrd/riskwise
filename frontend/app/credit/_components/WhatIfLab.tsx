import { ChevronRight, Sliders } from "lucide-react";
import { Card, CardHeader } from "@/components/ui";
import type { CreditScoreResponse } from "@/lib/api";
import { categoryStyle } from "../_lib/categories";
import type { useCreditAssessment } from "../_hooks/useCreditAssessment";

type WhatIf = ReturnType<typeof useCreditAssessment>["whatIf"];

function SliderRow({
  id,
  label,
  display,
  min,
  max,
  step,
  value,
  onChange,
}: {
  id: string;
  label: string;
  display: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <label htmlFor={id} className="text-slate-500 dark:text-slate-400">
          {label}
        </label>
        <span className="font-mono text-indigo-600 dark:text-indigo-300">{display}</span>
      </div>
      <input id={id} type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-indigo-500" />
    </div>
  );
}

function directionTone(direction: string): string {
  if (direction.includes("UPGRADED") || direction.includes("REDUCED")) {
    return "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40";
  }
  if (direction === "UNCHANGED") return "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400";
  return "bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800/40";
}

export default function WhatIfLab({ score, whatIf }: { score: CreditScoreResponse | null; whatIf: WhatIf }) {
  if (!score) return null;
  const { result } = whatIf;

  return (
    <Card className="space-y-4">
      <CardHeader
        className="border-b border-slate-200 dark:border-slate-800 pb-3"
        icon={<Sliders className="w-4 h-4 text-indigo-500" />}
        title="What-if Lab"
        right="Hypothetical simulation"
      />

      <div className="space-y-3">
        <SliderRow id="wi-missed" label="Missed payments" display={String(whatIf.missed)} min={0} max={10} value={whatIf.missed} onChange={whatIf.setMissed} />
        <SliderRow id="wi-enq" label="Enquiries (last 3 months)" display={String(whatIf.enquiries)} min={0} max={12} value={whatIf.enquiries} onChange={whatIf.setEnquiries} />
        <SliderRow
          id="wi-income"
          label="Monthly income"
          display={`₹${whatIf.income.toLocaleString("en-IN")}`}
          min={10000}
          max={150000}
          step={5000}
          value={whatIf.income}
          onChange={whatIf.setIncome}
        />
        <button
          type="button"
          onClick={whatIf.run}
          disabled={whatIf.loading}
          className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 text-white font-medium text-xs transition-colors disabled:opacity-60"
        >
          {whatIf.loading ? "Simulating…" : "Simulate Scenario Shift"}
        </button>
      </div>

      {result && (
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800 space-y-3 animate-fade-in text-xs">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[11px] text-slate-500 block">Baseline tier</span>
              <span className="font-mono font-bold text-slate-800 dark:text-slate-200">{result.baseline_category || score.predicted_category}</span>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-400" />
            <div className="text-right">
              <span className="text-[11px] text-slate-500 block">Simulated tier</span>
              <span className={`font-mono font-bold ${categoryStyle(result.counterfactual_category || score.predicted_category).text}`}>
                {result.counterfactual_category || "N/A"}
              </span>
            </div>
          </div>
          <div className="border-t border-slate-200 dark:border-slate-800 pt-2 flex items-center justify-between">
            <span className="text-slate-500">Shift direction</span>
            <span className={`font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${directionTone(result.direction_of_change)}`}>
              {result.direction_of_change}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 pt-1">Counterfactual simulations test how sensitive the model is to hypothetical changes in the inputs.</p>
        </div>
      )}
    </Card>
  );
}
