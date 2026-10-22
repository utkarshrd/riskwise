import { Info } from "lucide-react";
import { Alert, Badge, Skeleton } from "@/components/ui";

interface UniverseCardProps {
  symbols: string[];
  loading: boolean;
  loadError: string | null;
  onRetry: () => void;
  onAdd: (symbol: string) => void;
}

export default function UniverseCard({ symbols, loading, loadError, onRetry, onAdd }: UniverseCardProps) {
  return (
    <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
          <Info className="w-4 h-4 text-indigo-500" />
          <span>Preloaded Offline Snapshots (Instant)</span>
        </div>
        {!loadError && !loading && <Badge tone="green">{symbols.length} Cached</Badge>}
      </div>
      <p className="text-[11px] leading-relaxed">
        These instruments are cached locally with split and dividend adjusted prices for instant calculation.
        <strong className="block text-slate-700 dark:text-slate-300 mt-1">
          You can search for or enter any other NSE, BSE or US equity above. New symbols are validated and fetched on the fly.
        </strong>
      </p>

      {loading && (
        <div className="flex flex-wrap gap-1.5" aria-hidden="true">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-5 w-20" />
          ))}
        </div>
      )}

      {loadError && (
        <Alert
          tone="warning"
          action={
            <button type="button" onClick={onRetry} className="text-[11px] font-semibold underline shrink-0">
              Retry
            </button>
          }
        >
          Could not load the cached symbol list. {loadError}
        </Alert>
      )}

      {!loading && !loadError && (
        <div className="flex flex-wrap gap-1.5 pt-1 max-h-56 overflow-y-auto">
          {symbols.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onAdd(s)}
              title="Add to portfolio"
              className="px-2 py-0.5 rounded bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 hover:border-indigo-300 dark:hover:border-indigo-700 border border-slate-200 dark:border-slate-700 font-mono text-[10px] transition-colors text-slate-700 dark:text-slate-300"
            >
              + {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
