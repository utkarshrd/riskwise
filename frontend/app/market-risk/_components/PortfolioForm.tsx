import { Activity, Calendar, DollarSign, Sliders, Upload } from "lucide-react";
import NSEStockSearch from "@/components/NSEStockSearch";
import CurrencyAlerts from "@/components/portfolio/CurrencyAlerts";
import FxModeToggle from "@/components/portfolio/FxModeToggle";
import HoldingsEditor from "@/components/portfolio/HoldingsEditor";
import PresetPicker from "@/components/portfolio/PresetPicker";
import { Card, CardHeader, Field, inputClass, MetricInfo } from "@/components/ui";
import type { PortfolioBuilder } from "@/hooks/usePortfolioBuilder";
import type { AnalysisParams } from "../_hooks/useAnalysisParams";
import { useHoldingsImport } from "../_hooks/useHoldingsImport";
import HoldingsImportModal from "./HoldingsImportModal";
import { VAR_METHODS } from "../_lib/options";

interface PortfolioFormProps {
  builder: PortfolioBuilder;
  params: AnalysisParams;
  loading: boolean;
  onRun: () => void;
}

export default function PortfolioForm({ builder: b, params: p, loading, onRun }: PortfolioFormProps) {
  const importer = useHoldingsImport();
  const runDisabled = loading || b.blockedByCurrency || b.holdings.length === 0;

  return (
    <Card className="space-y-5">
      <CardHeader
        className="border-b border-slate-100 dark:border-slate-800 pb-3"
        icon={<Sliders className="w-4 h-4 text-indigo-500" />}
        title="Portfolio Setup"
        right={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={importer.openModal}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition border border-indigo-200/60 dark:border-indigo-800/60 shadow-sm"
              title="Import portfolio from Zerodha Kite, Groww, or custom CSV"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Import CSV</span>
            </button>
            <span className="font-mono text-slate-500">
              {b.currency} • {b.holdings.length} Assets
            </span>
          </div>
        }
      />

      <HoldingsImportModal
        isOpen={importer.isOpen}
        onClose={importer.closeModal}
        isUploading={importer.isUploading}
        result={importer.result}
        error={importer.error}
        fileName={importer.fileName}
        onUploadFile={importer.importFile}
        onReset={importer.reset}
        onApplyHoldings={b.loadImportedHoldings}
      />

      <PresetPicker presets={b.presets} selected={b.selectedPreset} onSelect={b.selectPreset} label="Benchmark Presets" />

      <div className="grid grid-cols-3 gap-3">
        <Field label="Portfolio Label" htmlFor="mr-name" className="col-span-2">
          <input id="mr-name" type="text" value={b.portfolioName} onChange={(e) => b.setPortfolioName(e.target.value)} className={inputClass} />
        </Field>
        <Field label="Currency" htmlFor="mr-currency">
          <select id="mr-currency" value={b.currency} onChange={(e) => b.changeCurrency(e.target.value)} className={inputClass}>
            <option value="USD">USD ($)</option>
            <option value="INR">INR (₹)</option>
          </select>
        </Field>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between items-center text-xs">
          <label htmlFor="mr-value" className="font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1">
            <DollarSign className="w-3.5 h-3.5 text-slate-400" />
            Portfolio Value ({b.currency})
          </label>
          <div className="flex items-center gap-1 text-[11px] text-slate-500">
            {(["weight", "value"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => b.setInputMode(mode)}
                aria-pressed={b.inputMode === mode}
                className={`px-1.5 py-0.5 rounded ${
                  b.inputMode === mode
                    ? "bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-semibold"
                    : "hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                {mode === "weight" ? "By Weight" : "By Value"}
              </button>
            ))}
          </div>
        </div>
        <input
          id="mr-value"
          type="number"
          min="1000"
          step="5000"
          value={b.portfolioValue}
          onChange={(e) => b.setPortfolioValue(Number(e.target.value))}
          className={`${inputClass} font-mono`}
        />
      </div>

      <NSEStockSearch
        onSelectSymbol={(symbol, name, currency) => b.addAsset({ symbol, name, currency })}
        activeCurrency={b.fxMode === "strict" ? b.currency : ""}
        disabledSymbols={b.holdings.map((h) => h.symbol)}
      />

      <HoldingsEditor
        holdings={b.holdings}
        currency={b.currency}
        portfolioValue={b.portfolioValue}
        inputMode={b.inputMode}
        totalWeight={b.totalWeight}
        totalPositionValue={b.totalPositionValue}
        onChange={b.changeHolding}
        onRemove={b.removeHolding}
        onNormalize={b.normalizeWeights}
      />

      <FxModeToggle value={b.fxMode} onChange={b.setFxMode} baseCurrency={b.currency} />

      <CurrencyAlerts
        currency={b.currency}
        distinctCurrencies={b.distinctCurrencies}
        hasMixedCurrencies={b.hasMixedCurrencies}
        currencyMismatch={b.currencyMismatch}
        fxMode={b.fxMode}
        onSetCurrency={b.changeCurrency}
        onEnableConversion={() => b.setFxMode("convert_to_base")}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
        <Field
          htmlFor="mr-lookback"
          label={
            <>
              <Calendar className="w-3 h-3 text-slate-400" /> Lookback Period
            </>
          }
        >
          <select id="mr-lookback" value={p.lookbackDays} onChange={(e) => p.setLookbackDays(Number(e.target.value))} className={inputClass}>
            <option value={60}>60 Trading Days</option>
            <option value={120}>120 Trading Days</option>
            <option value={252}>252 Days (1 Year)</option>
            <option value={500}>500 Days (2 Years)</option>
          </select>
        </Field>

        <Field label="Return Formulation" htmlFor="mr-return">
          <select id="mr-return" value={p.returnMethod} onChange={(e) => p.setReturnMethod(e.target.value)} className={inputClass}>
            <option value="simple">Discrete Simple Returns</option>
            <option value="log">Log Returns (ln(P_t/P_0))</option>
          </select>
        </Field>

        <Field
          htmlFor="mr-var-method"
          label={
            <>
              VaR Model <MetricInfo metric={VAR_METHODS.find((m) => m.value === p.varMethod)?.metric ?? "historical_var"} />
            </>
          }
        >
          <select id="mr-var-method" value={p.varMethod} onChange={(e) => p.setVarMethod(e.target.value)} className={`${inputClass} font-medium`}>
            {VAR_METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Holding Horizon" htmlFor="mr-horizon">
          <select id="mr-horizon" value={p.horizonDays} onChange={(e) => p.setHorizonDays(Number(e.target.value))} className={`${inputClass} font-mono`}>
            <option value={1}>1 Trading Day (Daily)</option>
            <option value={5}>5 Trading Days (1 Week)</option>
            <option value={10}>10 Trading Days (Basel)</option>
            <option value={20}>20 Trading Days (1 Month)</option>
          </select>
        </Field>
      </div>

      <button
        type="button"
        onClick={onRun}
        disabled={runDisabled}
        className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
      >
        <Activity className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        {loading ? "Computing Risk Metrics…" : b.blockedByCurrency ? "Resolve Currency Mismatch to Proceed" : "Run Portfolio Risk Assessment"}
      </button>
    </Card>
  );
}
