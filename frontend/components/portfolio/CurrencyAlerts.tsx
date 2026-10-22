import { Alert } from "@/components/ui";
import type { FxMode } from "@/lib/api";

interface CurrencyAlertsProps {
  currency: string;
  distinctCurrencies: string[];
  hasMixedCurrencies: boolean;
  currencyMismatch: boolean;
  fxMode: FxMode;
  onSetCurrency: (currency: string) => void;
  onEnableConversion: () => void;
}

const actionClass =
  "px-2 py-1 rounded text-[11px] font-semibold bg-amber-200/80 dark:bg-amber-800 text-amber-900 dark:text-amber-100 hover:bg-amber-300 dark:hover:bg-amber-700 transition-colors shrink-0";

/** Explains the single-currency rule, and the FX conversion that replaces it when the user opts in. */
export default function CurrencyAlerts({
  currency,
  distinctCurrencies,
  hasMixedCurrencies,
  currencyMismatch,
  fxMode,
  onSetCurrency,
  onEnableConversion,
}: CurrencyAlertsProps) {
  if (fxMode === "convert_to_base") {
    const foreign = distinctCurrencies.filter((c) => c !== currency);
    if (foreign.length === 0) return null;
    return (
      <Alert tone="info" title="FX conversion is on">
        {foreign.join(" and ")} assets will be converted into <strong>{currency}</strong> with the historical USD/INR rate for every day, so
        returns include currency movement. The results state the FX series and date range used.
      </Alert>
    );
  }

  if (hasMixedCurrencies) {
    return (
      <Alert
        tone="error"
        title="Mixed currencies"
        action={
          <button type="button" onClick={onEnableConversion} className={actionClass}>
            Convert to {currency}
          </button>
        }
      >
        This portfolio mixes <strong>{distinctCurrencies.join(" and ")}</strong>. Portfolios are single-currency by default, with no silent FX
        assumptions. Remove the mismatched assets, or opt in to converting everything into {currency}.
      </Alert>
    );
  }

  if (currencyMismatch) {
    return (
      <Alert
        tone="warning"
        action={
          <button type="button" onClick={() => onSetCurrency(distinctCurrencies[0])} className={actionClass}>
            Set to {distinctCurrencies[0]}
          </button>
        }
      >
        Portfolio base currency is <strong>{currency}</strong>, but the assets are denominated in <strong>{distinctCurrencies[0]}</strong>.
      </Alert>
    );
  }
  return null;
}
