export function formatCurrency(n: number | null | undefined, currency: string): string {
  if (n == null) return "N/A";
  return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(n);
}

/** Fractions in, percent string out: 0.0214 -> "2.14%". */
export function formatPct(n: number | null | undefined, digits = 2): string {
  if (n == null) return "N/A";
  return `${(n * 100).toFixed(digits)}%`;
}

export function formatNumber(n: number | null | undefined, digits = 2): string {
  return n == null ? "N/A" : n.toFixed(digits);
}
