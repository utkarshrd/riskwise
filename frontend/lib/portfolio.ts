export type SymbolState = "verified_snapshot" | "live_validated" | "not_available" | "validating";

export interface HoldingRow {
  symbol: string;
  name?: string;
  exchange?: string;
  currency?: string;
  weight: number;
  position_value?: number;
  state?: SymbolState;
  observations_count?: number;
  alias_note?: string;
}

export type InputMode = "weight" | "value";

export interface Preset {
  name: string;
  currency: string;
  holdings: HoldingRow[];
  defaultVal: number;
}

export type PresetMap = Record<string, Preset>;

export function withPositionValues(preset: Preset): HoldingRow[] {
  return preset.holdings.map((h) => ({ ...h, position_value: Math.round(h.weight * preset.defaultVal) }));
}

export function inferSymbolCurrency(sym: string, portfolioCurrency?: string): string {
  const upper = sym.toUpperCase().trim();
  if (upper.endsWith(".NS") || upper.endsWith(".BO") || upper.startsWith("^NSE") || upper.startsWith("_NSE")) {
    return "INR";
  }
  if (upper.endsWith(".TO") || upper.endsWith(".L") || upper.endsWith(".DE") || upper.endsWith(".PA")) {
    return "USD";
  }
  if (!upper.includes(".") && portfolioCurrency === "INR") {
    return "INR";
  }
  return "USD";
}
