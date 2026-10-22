"use client";

import { useState } from "react";
import { api, type FxMode } from "@/lib/api";
import {
  inferSymbolCurrency,
  withPositionValues,
  type HoldingRow,
  type InputMode,
  type PresetMap,
} from "@/lib/portfolio";

interface BuilderOptions {
  presets: PresetMap;
  defaultPreset: string;
  /** Called when adding or validating a symbol fails in a way the user should see (null clears it). */
  onProblem: (message: string | null) => void;
  /** Called with the canonical symbol once the server has confirmed it has price data. */
  onSymbolVerified?: (symbol: string) => void;
  /** Called when a preset replaces the portfolio so stale results can be dropped. */
  onPortfolioReset: () => void;
}

export interface NewAsset {
  symbol: string;
  name?: string;
  exchange?: string;
  currency?: string;
}

/** Portfolio composition state shared by the Market Risk and VaR Validation pages. */
export function usePortfolioBuilder({ presets, defaultPreset, onProblem, onSymbolVerified, onPortfolioReset }: BuilderOptions) {
  const initial = presets[defaultPreset];
  const [selectedPreset, setSelectedPreset] = useState(defaultPreset);
  const [portfolioName, setPortfolioName] = useState(initial.name.replace(/ \(.*\)$/, ""));
  const [currency, setCurrency] = useState(initial.currency);
  const [portfolioValue, setPortfolioValue] = useState(initial.defaultVal);
  const [inputMode, setInputMode] = useState<InputMode>("weight");
  const [holdings, setHoldings] = useState<HoldingRow[]>(() => withPositionValues(initial));
  // strict (default) keeps every portfolio single-currency; convert_to_base is an explicit opt-in
  const [fxMode, setFxMode] = useState<FxMode>("strict");
  const strict = fxMode === "strict";

  const totalWeight = holdings.reduce((sum, h) => sum + (h.weight || 0), 0);
  const totalPositionValue = holdings.reduce((sum, h) => sum + (h.position_value || 0), 0);

  const distinctCurrencies = Array.from(new Set(holdings.map((h) => h.currency || inferSymbolCurrency(h.symbol))));
  const hasMixedCurrencies = distinctCurrencies.length > 1;
  const currencyMismatch = strict && !hasMixedCurrencies && !!distinctCurrencies[0] && distinctCurrencies[0] !== currency;
  /** Mixed currencies only block a run while conversion has not been opted into. */
  const blockedByCurrency = strict && hasMixedCurrencies;

  const selectPreset = (key: string) => {
    const preset = presets[key];
    if (!preset) return;
    setSelectedPreset(key);
    setPortfolioName(preset.name);
    setCurrency(preset.currency);
    setPortfolioValue(preset.defaultVal);
    setHoldings(withPositionValues(preset));
    onPortfolioReset();
  };

  const changeCurrency = (next: string) => {
    setCurrency(next);
    setSelectedPreset("custom");
  };

  const addAsset = async (item: NewAsset) => {
    let rawSym = item.symbol.toUpperCase().trim();
    if (strict && currency === "INR" && !rawSym.includes(".") && !rawSym.startsWith("^")) {
      rawSym = `${rawSym}.NS`;
    }
    if (holdings.some((h) => h.symbol === rawSym)) {
      onProblem(`Symbol '${rawSym}' is already included in your portfolio.`);
      return;
    }

    const itemCurrency = item.currency || inferSymbolCurrency(rawSym, currency);
    if (holdings.length === 0 && strict) setCurrency(itemCurrency);

    const newWeight = holdings.length === 0 ? 1.0 : 0.1;
    setSelectedPreset("custom");
    setHoldings((prev) => [
      ...prev,
      {
        symbol: rawSym,
        name: item.name || rawSym,
        exchange: item.exchange || (itemCurrency === "INR" ? "NSE" : "US"),
        currency: itemCurrency,
        weight: newWeight,
        position_value: Math.round(newWeight * portfolioValue),
        state: "validating",
      },
    ]);
    onProblem(null);

    try {
      const res = await api.market.validateSymbol(rawSym, strict ? currency : undefined);
      setHoldings((prev) =>
        prev.map((h) =>
          h.symbol === rawSym
            ? {
                ...h,
                symbol: res.canonical_symbol,
                name: res.name || h.name,
                exchange: res.exchange || h.exchange,
                currency: res.currency || h.currency,
                state: res.state,
                observations_count: res.observations_count || undefined,
                alias_note: res.alias_note || undefined,
              }
            : h
        )
      );
      if (res.state === "not_available") {
        onProblem(`${rawSym}: ${res.message}`);
      } else {
        onSymbolVerified?.(res.canonical_symbol);
      }
    } catch (err) {
      // Mark the row so it does not stay on "Validating…" forever
      setHoldings((prev) => prev.map((h) => (h.symbol === rawSym ? { ...h, state: "not_available" } : h)));
      onProblem(`Could not validate ${rawSym}: ${err instanceof Error ? err.message : "unknown error"}`);
    }
  };

  const changeHolding = (index: number, field: "symbol" | "weight" | "position_value", value: string | number) => {
    setSelectedPreset("custom");
    setHoldings((prev) => {
      const updated = [...prev];
      if (field === "symbol") {
        const sym = String(value).toUpperCase().trim();
        updated[index] = { ...updated[index], symbol: sym, currency: inferSymbolCurrency(sym) };
      } else if (field === "weight") {
        const w = Number(value);
        updated[index] = { ...updated[index], weight: w, position_value: Math.round(w * portfolioValue) };
      } else {
        updated[index] = { ...updated[index], position_value: Number(value) };
      }
      return updated;
    });
  };

  const removeHolding = (index: number) => {
    if (holdings.length <= 1) return;
    setSelectedPreset("custom");
    setHoldings((prev) => prev.filter((_, i) => i !== index));
  };

  const normalizeWeights = () => {
    if (inputMode === "value" && totalPositionValue > 0) {
      setHoldings((prev) =>
        prev.map((h) => ({ ...h, weight: Number(((h.position_value || 0) / totalPositionValue).toFixed(4)) }))
      );
      setPortfolioValue(totalPositionValue);
    } else if (totalWeight > 0) {
      setHoldings((prev) =>
        prev.map((h) => ({
          ...h,
          weight: Number((h.weight / totalWeight).toFixed(4)),
          position_value: Math.round((h.weight / totalWeight) * portfolioValue),
        }))
      );
    }
  };

  /** Request body holdings: weights, or position values when the user is entering monetary amounts. */
  const payloadHoldings = () =>
    inputMode === "value"
      ? holdings.map((h) => ({ symbol: h.symbol, position_value: h.position_value }))
      : holdings.map((h) => ({ symbol: h.symbol, weight: Number(h.weight) }));

  const loadImportedHoldings = (
    imported: Array<{
      symbol: string;
      name?: string;
      currency?: string;
      weight: number;
      position_value?: number;
    }>,
    inferredCurrency?: string | null,
    totalValue?: number
  ) => {
    setSelectedPreset("custom");
    if (inferredCurrency) {
      setCurrency(inferredCurrency);
    } else {
      // Mixed currencies: automatically opt into convert_to_base so analysis isn't blocked
      setFxMode("convert_to_base");
    }
    if (totalValue && totalValue > 0) {
      setPortfolioValue(Math.round(totalValue));
    }
    setHoldings(
      imported.map((item) => ({
        symbol: item.symbol,
        name: item.name || item.symbol,
        currency: item.currency || inferSymbolCurrency(item.symbol, inferredCurrency || currency),
        weight: Number(item.weight),
        position_value: item.position_value
          ? Math.round(item.position_value)
          : Math.round(item.weight * (totalValue || portfolioValue)),
        state: "verified_snapshot",
      }))
    );
    onPortfolioReset();
  };

  return {
    presets,
    selectedPreset,
    portfolioName,
    currency,
    portfolioValue,
    inputMode,
    holdings,
    totalWeight,
    totalPositionValue,
    distinctCurrencies,
    hasMixedCurrencies,
    currencyMismatch,
    blockedByCurrency,
    fxMode,
    setFxMode,
    setPortfolioName,
    setPortfolioValue,
    setInputMode,
    selectPreset,
    changeCurrency,
    addAsset,
    changeHolding,
    removeHolding,
    normalizeWeights,
    payloadHoldings,
    loadImportedHoldings,
  };
}

export type PortfolioBuilder = ReturnType<typeof usePortfolioBuilder>;
