import { History } from "lucide-react";
import type { VaRValidationHistoryItem } from "@/lib/api";
import { Alert, Badge, Card, CardHeader, MetricInfo, Skeleton, type Tone } from "@/components/ui";

const ZONE_TONE: Record<string, Tone> = { GREEN: "green", YELLOW: "amber", RED: "red" };

interface RunHistoryProps {
  runs: VaRValidationHistoryItem[];
  loading: boolean;
  error: string | null;
}

export default function RunHistory({ runs, loading, error }: RunHistoryProps) {
  return (
    <Card className="space-y-3">
      <CardHeader
        className="border-b border-slate-100 dark:border-slate-800 pb-2"
        icon={<History className="w-4 h-4 text-slate-500" />}
        title="Saved Runs"
        right="Stored in the local database"
      />

      {loading && (
        <div className="space-y-2" role="status">
          <span className="sr-only">Loading saved runs…</span>
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14" />
          ))}
        </div>
      )}

      {error && !loading && <Alert tone="warning">Could not load saved runs. {error}</Alert>}

      {!loading && !error && runs.length === 0 && (
        <div className="text-center py-4 text-xs text-slate-400">No validation runs saved yet.</div>
      )}

      {!loading && runs.length > 0 && (
        <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
          {runs.map((hr) => (
            <div
              key={hr.id}
              className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 text-xs space-y-1"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">{hr.portfolio_name}</span>
                <Badge tone={ZONE_TONE[hr.basel_zone ?? ""] ?? "neutral"} className="font-bold">
                  {hr.basel_zone || "N/A"}
                </Badge>
              </div>
              <div className="flex justify-between gap-2 text-[10px] text-slate-500 font-mono">
                <span>
                  {hr.method} • {Math.round(hr.confidence_level * 1000) / 10}%
                </span>
                <span>
                  {hr.exception_count}/{hr.forecast_count} exc ({(hr.exception_rate * 100).toFixed(1)}%)
                </span>
              </div>
              <div className="text-[10px] text-slate-400 flex justify-between items-center gap-2">
                <span className="inline-flex items-center gap-1">
                  Kupiec p: {hr.kupiec_p_value != null ? hr.kupiec_p_value.toFixed(4) : "N/A"}
                  <MetricInfo metric="kupiec" />
                </span>
                <span>{hr.created_at ? hr.created_at.slice(0, 10) : ""}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
