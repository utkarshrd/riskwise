import { Alert } from "@/components/ui";

interface CurrencyAlertsProps {
  currency: string;
  distinctCurrencies: string[];
  hasMixedCurrencies: boolean;
  currencyMismatch: boolean;
  onSetCurrency: (currency: string) => void;
}

/** Explains the single-currency rule and offers a one-click fix for a mismatched base currency. */
export default function CurrencyAlerts({
  currency,
  distinctCurrencies,
  hasMixedCurrencies,
  currencyMismatch,
  onSetCurrency,
}: CurrencyAlertsProps) {
  if (hasMixedCurrencies) {
    return (
      <Alert tone="error" title="Incompatible currencies detected">
        Your portfolio combines assets with different base currencies: <strong>{distinctCurrencies.join(" and ")}</strong>. RiskWise
        requires single-currency portfolios and makes no silent FX assumptions. Keep only INR or only USD assets.
      </Alert>
    );
  }
  if (currencyMismatch) {
    return (
      <Alert
        tone="warning"
        action={
          <button
            type="button"
            onClick={() => onSetCurrency(distinctCurrencies[0])}
            className="px-2 py-1 rounded text-[11px] font-semibold bg-amber-200/80 dark:bg-amber-800 text-amber-900 dark:text-amber-100 hover:bg-amber-300 dark:hover:bg-amber-700 transition-colors shrink-0"
          >
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
