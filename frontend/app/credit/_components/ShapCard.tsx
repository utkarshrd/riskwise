import { TrendingDown, TrendingUp, Zap } from "lucide-react";
import { Card, CardHeader } from "@/components/ui";
import type { CreditExplainResponse } from "@/lib/api";
import { featureLabel } from "../_lib/fields";

export default function ShapCard({ explain }: { explain: CreditExplainResponse | null }) {
  if (!explain?.top_contributions?.length) return null;

  return (
    <Card className="space-y-4">
      <CardHeader
        className="border-b border-slate-200 dark:border-slate-800 pb-3"
        icon={<Zap className="w-4 h-4 text-amber-500" />}
        title="Why this category (SHAP)"
        right={<span className="font-mono">Impact on tier {explain.predicted_category}</span>}
      />
      <p className="text-[11px] text-slate-500">
        Each row shows how much one input pushed the model toward or away from this tier. Larger numbers mean a bigger push.
      </p>
      <div className="space-y-2.5">
        {explain.top_contributions.map((c) => {
          const reducesRisk = c.impact_direction === "REDUCES_RISK";
          return (
            <div
              key={c.feature_name}
              className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 flex items-center justify-between gap-3 text-xs"
            >
              <div className="space-y-0.5 min-w-0">
                <span className="font-medium text-slate-800 dark:text-slate-200 block truncate">{featureLabel(c.feature_name)}</span>
                <span className="text-[11px] text-slate-500 font-mono">Value: {String(c.feature_value)}</span>
              </div>
              <div className="text-right flex items-center gap-2 shrink-0">
                <div className="space-y-0.5">
                  <span className={`font-mono font-semibold block ${reducesRisk ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`}>
                    {c.shap_value > 0 ? `+${c.shap_value.toFixed(4)}` : c.shap_value.toFixed(4)}
                  </span>
                  <span className="text-[10px] text-slate-500">{reducesRisk ? "Favorable" : "Stress driver"}</span>
                </div>
                {reducesRisk ? (
                  <TrendingDown className="w-4 h-4 text-emerald-500" />
                ) : (
                  <TrendingUp className="w-4 h-4 text-rose-500" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
