import { CreditCard } from "lucide-react";
import { Alert, EmptyState, Skeleton } from "@/components/ui";
import type { CreditScoreResponse } from "@/lib/api";
import { categoryStyle } from "../_lib/categories";

interface PredictionCardProps {
  score: CreditScoreResponse | null;
  loading: boolean;
}

export default function PredictionCard({ score, loading }: PredictionCardProps) {
  if (loading) {
    return (
      <div className="space-y-3" role="status">
        <span className="sr-only">Scoring profile…</span>
        <Skeleton className="h-28 rounded-2xl" />
        <Skeleton className="h-36 rounded-2xl" />
      </div>
    );
  }

  if (!score) {
    return (
      <EmptyState
        icon={<CreditCard className="w-8 h-8" />}
        title="No assessment yet"
        description={
          <>
            Pick a reference profile or adjust the features, then click <strong>Score & Explain Profile</strong>.
          </>
        }
      />
    );
  }

  const style = categoryStyle(score.predicted_category);

  return (
    <div className={`p-5 sm:p-6 rounded-2xl border ${style.border} ${style.panel} space-y-5 animate-fade-in`}>
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <span className="text-xs font-mono uppercase tracking-wider text-slate-500 dark:text-slate-400">Predicted Credit Category</span>
          <div className="flex items-baseline gap-3 mt-1">
            <span className={`text-4xl font-extrabold font-mono ${style.text}`}>{score.predicted_category}</span>
            <span className="text-sm font-medium text-slate-600 dark:text-slate-300">Category {score.predicted_category}</span>
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs text-slate-500 block">Model version</span>
          <span className="text-xs font-mono text-indigo-600 dark:text-indigo-300">{score.model_version}</span>
        </div>
      </div>

      {score.class_probabilities && (
        <div className="space-y-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 block">
            Model class probabilities
          </span>
          <p className="text-[10px] text-slate-500">
            Raw multiclass model outputs for each dataset category. They are not calibrated probabilities of default.
          </p>
          <div className="space-y-1.5">
            {Object.entries(score.class_probabilities).map(([cls, prob]) => {
              const s = categoryStyle(cls);
              const pct = Math.round(prob * 100);
              const winner = cls === score.predicted_category;
              return (
                <div key={cls} className="space-y-0.5">
                  <div className="flex justify-between text-xs">
                    <span className={`font-mono font-bold ${winner ? s.text : "text-slate-500"}`}>
                      {cls} {winner ? "★ predicted" : ""}
                    </span>
                    <span className="font-mono text-slate-600 dark:text-slate-300">
                      {pct}% ({prob.toFixed(4)})
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-200 dark:bg-slate-900 rounded-full overflow-hidden">
                    <div className={`h-full ${s.bar} transition-all duration-500`} style={{ width: `${Math.max(pct, 2)}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {score.warnings && score.warnings.length > 0 && (
        <Alert tone="warning" title="Input validation notice">
          <ul className="list-disc list-inside space-y-0.5">
            {score.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Alert>
      )}

      <p className="text-[11px] text-slate-500 leading-relaxed border-t border-slate-200 dark:border-slate-800 pt-3">
        {score.proxy_dataset_disclaimer || "Predictions are relative classifications within historical benchmarks and do not guarantee credit approval."}
      </p>
    </div>
  );
}
