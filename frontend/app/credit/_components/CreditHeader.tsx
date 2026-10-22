import { CreditCard, Zap } from "lucide-react";
import { Alert, Badge } from "@/components/ui";

interface CreditHeaderProps {
  loading: boolean;
  onScore: () => void;
}

export default function CreditHeader({ loading, onScore }: CreditHeaderProps) {
  return (
    <>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-600 dark:text-indigo-400">
            <CreditCard className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex flex-wrap items-center gap-3">
              Indian Credit Risk Intelligence
              <Badge tone="green" className="font-mono">
                Multiclass P1–P4
              </Badge>
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Explainable four-tier credit risk classification benchmarked on 51,336 Indian banking & CIBIL records.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onScore}
          disabled={loading}
          className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-600/20"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              Scoring & Explaining…
            </>
          ) : (
            <>
              <Zap className="w-4 h-4" />
              Score & Explain Profile
            </>
          )}
        </button>
      </div>

      <Alert tone="info">
        <span className="font-semibold">Methodological disclosure:</span> this assessment predicts relative credit tiers (<code>P1</code>–<code>P4</code>) with an XGBoost multiclass model trained on a 70/15/15 stratified split of Indian banking and bureau data (51,336 records). The tiers are the dataset&apos;s own <code>Approved_Flag</code> values. They express relative risk within this dataset and are not regulated CIBIL score bands or official default categories. The tool does <strong>not</strong> estimate a CIBIL score, compute a probability of default, or guarantee credit approval.
      </Alert>
    </>
  );
}
