import { CheckCircle2, Sparkles } from "lucide-react";
import { Alert, Card, Skeleton } from "@/components/ui";
import type { BorrowerProfileSample } from "@/lib/api";
import { categoryStyle } from "../_lib/categories";

interface SampleSelectorProps {
  samples: BorrowerProfileSample[];
  loading: boolean;
  error: string | null;
  selectedId: string;
  onSelect: (id: string) => void;
}

export default function SampleSelector({ samples, loading, error, selectedId, onSelect }: SampleSelectorProps) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-3 gap-2">
        <span className="text-xs font-semibold tracking-wider uppercase text-slate-500 dark:text-slate-400 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-500" />
          Reference Profiles
        </span>
        <span className="text-xs text-slate-400">Non-sensitive example cases</span>
      </div>

      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2" role="status">
          <span className="sr-only">Loading reference profiles…</span>
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      )}

      {error && !loading && (
        <Alert tone="warning">Could not load reference profiles, so you can still enter a profile by hand. {error}</Alert>
      )}

      {!loading && samples.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {samples.map((s) => {
            const selected = selectedId === s.sample_id;
            const style = categoryStyle(s.expected_category);
            return (
              <button
                key={s.sample_id}
                type="button"
                onClick={() => onSelect(s.sample_id)}
                aria-pressed={selected}
                className={`p-3 rounded-xl text-left border transition-all ${
                  selected
                    ? "bg-indigo-50 dark:bg-indigo-600/10 border-indigo-500 shadow-md shadow-indigo-500/10"
                    : "bg-slate-50 dark:bg-slate-950/60 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${style.chip}`}>{s.expected_category}</span>
                  {selected && <CheckCircle2 className="w-3.5 h-3.5 text-indigo-500" />}
                </div>
                <p className="text-xs font-medium text-slate-800 dark:text-slate-200 mt-2 line-clamp-1">{s.label}</p>
                <p className="text-[11px] text-slate-500 line-clamp-1">{s.description.split(",")[0]}</p>
              </button>
            );
          })}
        </div>
      )}
    </Card>
  );
}
