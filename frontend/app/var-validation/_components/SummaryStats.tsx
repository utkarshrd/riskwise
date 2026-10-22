import { AlertTriangle, CheckCircle2 } from "lucide-react";
import type { VaRValidationResponse } from "@/lib/api";
import { Stat } from "@/components/ui";
import { formatPct } from "@/lib/format";

export default function SummaryStats({ result }: { result: VaRValidationResponse }) {
  const zoneTone = result.basel_zone === "GREEN" ? "good" : result.basel_zone === "YELLOW" ? "warn" : "bad";

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Stat label="Evaluated Forecasts (N)" value={result.forecast_count} hint="Total out-of-sample days" />
      <Stat
        label="Observed Exceptions (x)"
        tone={result.exception_count > result.expected_exceptions * 1.5 ? "bad" : "good"}
        value={result.exception_count}
        hint={`Expected: ${result.expected_exceptions.toFixed(1)}`}
      />
      <Stat
        label="Exception Rate"
        value={formatPct(result.exception_rate)}
        hint={`Nominal: ${formatPct(result.expected_exception_rate)}`}
      />
      <Stat
        label="Basel Zone"
        metric="basel"
        tone={zoneTone}
        value={
          <span className="flex items-center gap-1.5 text-base">
            {result.basel_zone === "GREEN" ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            {result.basel_zone}
          </span>
        }
        hint={`Cumulative probability: ${(result.basel_zone_cumulative_prob * 100).toFixed(2)}%`}
      />
    </div>
  );
}
