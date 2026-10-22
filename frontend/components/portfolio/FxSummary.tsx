import type { FxInfo } from "@/lib/api";
import { Alert } from "@/components/ui";

/** States exactly which FX series and dates the converted results rest on. Renders nothing when no conversion happened. */
export default function FxSummary({ fx }: { fx?: FxInfo | null }) {
  if (!fx?.fx_converted) return null;

  const directions = Object.entries(fx.conversion_directions ?? {})
    .map(([sym, dir]) => `${sym} (${dir.replace("->", " → ")})`)
    .join(", ");

  return (
    <Alert tone="info" title={`Converted to ${fx.base_currency} with ${fx.fx_pair}`}>
      <ul className="mt-1 space-y-0.5">
        <li>
          <strong>Converted holdings:</strong> {directions}
        </li>
        <li>
          <strong>FX series used:</strong> {fx.series_start} to {fx.series_end} ({fx.observations} daily rates, source: {fx.fx_data_source?.replace(/_/g, " ")})
        </li>
        <li>
          <strong>Rate at start and end:</strong> {fx.rate_start} and {fx.rate_end} INR per USD
        </li>
      </ul>
      <p className="mt-1 text-[11px] opacity-80">Returns include the currency movement, and position sizes are read as {fx.base_currency} amounts.</p>
    </Alert>
  );
}
