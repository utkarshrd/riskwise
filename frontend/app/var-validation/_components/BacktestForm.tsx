import { Activity, Calendar, Sliders } from "lucide-react";
import NSEStockSearch from "@/components/NSEStockSearch";
import CurrencyAlerts from "@/components/portfolio/CurrencyAlerts";
import HoldingsEditor from "@/components/portfolio/HoldingsEditor";
import PresetPicker from "@/components/portfolio/PresetPicker";
import { Card, CardHeader, Field, inputClass, MetricInfo } from "@/components/ui";
import type { PortfolioBuilder } from "@/hooks/usePortfolioBuilder";
import { WINDOW_OPTIONS } from "../_lib/options";

interface BacktestFormProps {
  builder: PortfolioBuilder;
  method: string;
  onMethodChange: (method: string) => void;
  confidenceLevel: number;
  onConfidenceChange: (level: number) => void;
  lookbackWindow: number;
  onWindowChange: (days: number) => void;
  loading: boolean;
  onRun: () => void;
}

export default function BacktestForm({
  builder: b,
  method,
  onMethodChange,
  confidenceLevel,
  onConfidenceChange,
  lookbackWindow,
  onWindowChange,
  loading,
  onRun,
}: BacktestFormProps) {
  return (
    <Card className="space-y-5">
      <CardHeader
        className="border-b border-slate-100 dark:border-slate-800 pb-3"
        icon={<Sliders className="w-4 h-4 text-emerald-500" />}
        title="Backtest Setup"
        right={<span className="font-mono">Rolling, out-of-sample</span>}
      />

      <PresetPicker presets={b.presets} selected={b.selectedPreset} onSelect={b.selectPreset} label="Portfolio Presets" accent="emerald" showWeights />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Field
          htmlFor="vv-method"
          label={
            <>
              Risk Methodology <MetricInfo metric={method === "parametric" ? "parametric_var" : "historical_var"} />
            </>
          }
        >
          <select id="vv-method" value={method} onChange={(e) => onMethodChange(e.target.value)} className={inputClass}>
            <option value="historical">Historical Simulation</option>
            <option value="parametric">Parametric Gaussian</option>
          </select>
        </Field>
        <Field htmlFor="vv-confidence" label="Confidence Level">
          <select id="vv-confidence" value={confidenceLevel} onChange={(e) => onConfidenceChange(Number(e.target.value))} className={inputClass}>
            <option value={0.95}>95.0% VaR (p0 = 5.0%)</option>
            <option value={0.99}>99.0% VaR (p0 = 1.0%)</option>
          </select>
        </Field>
      </div>

      <Field
        htmlFor="vv-window"
        label={
          <>
            <Calendar className="w-3.5 h-3.5 text-slate-400" /> Rolling Estimation Window (Trading Days)
          </>
        }
        hint={
          <>
            Each forecast on day <code>t</code> is estimated from the previous <code>{lookbackWindow}</code> observations only.
          </>
        }
      >
        <select id="vv-window" value={lookbackWindow} onChange={(e) => onWindowChange(Number(e.target.value))} className={inputClass}>
          {WINDOW_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </Field>

      <NSEStockSearch
        onSelectSymbol={(symbol, name, currency) => b.addAsset({ symbol, name, currency })}
        activeCurrency={b.currency}
        disabledSymbols={b.holdings.map((h) => h.symbol)}
      />

      <HoldingsEditor
        holdings={b.holdings}
        currency={b.currency}
        portfolioValue={b.portfolioValue}
        inputMode="weight"
        totalWeight={b.totalWeight}
        totalPositionValue={b.totalPositionValue}
        showAmounts={false}
        onChange={b.changeHolding}
        onRemove={b.removeHolding}
        onNormalize={b.normalizeWeights}
      />

      <CurrencyAlerts
        currency={b.currency}
        distinctCurrencies={b.distinctCurrencies}
        hasMixedCurrencies={b.hasMixedCurrencies}
        currencyMismatch={b.currencyMismatch}
        onSetCurrency={b.changeCurrency}
      />

      <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-0.5">
        <div className="font-medium text-slate-700 dark:text-slate-300">Minimum observations</div>
        <div>
          Needs the estimation window (<code>{lookbackWindow} days</code>) plus at least 10 out-of-sample days, so about{" "}
          <strong>{lookbackWindow + 11}+ trading sessions</strong>.
        </div>
      </div>

      <button
        type="button"
        onClick={onRun}
        disabled={loading || b.hasMixedCurrencies || b.holdings.length === 0}
        className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
      >
        <Activity className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        {loading ? "Running Rolling VaR Backtest…" : b.hasMixedCurrencies ? "Resolve Currency Mismatch to Proceed" : "Execute Rolling VaR Validation"}
      </button>
    </Card>
  );
}
