"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Loader2, Tag, Layers, Check, Plus } from "lucide-react";
import { api, StockSearchResult } from "@/lib/api";

interface NSEStockSearchProps {
  onSelectSymbol: (symbol: string, name?: string, currency?: string) => void;
  activeCurrency: string;
  disabledSymbols?: string[];
}

const POPULAR_INDEX_CHIPS = ["NIFTY 50", "NIFTY BANK", "NIFTY IT", "S&P 500"];
const POPULAR_SECTOR_CHIPS = [
  "Financial Services",
  "Information Technology",
  "Automobile",
  "Energy",
  "Broad Market",
];
const CAP_CHIPS = ["Large Cap", "Mid Cap", "Small Cap"];

export default function NSEStockSearch({
  onSelectSymbol,
  activeCurrency,
  disabledSymbols = [],
}: NSEStockSearchProps) {
  const [query, setQuery] = useState("");
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<string | null>(null);
  const [selectedCap, setSelectedCap] = useState<string | null>(null);
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const hasCriteria = Boolean(query.trim() || selectedSector || selectedIndex || selectedCap);
  // Stale results are never shown once the criteria are cleared
  const visibleResults = hasCriteria ? results : [];

  // Debounced search when query or filter chips change
  useEffect(() => {
    if (!hasCriteria) return;

    let cancelled = false;
    const timer = setTimeout(async () => {
      setLoading(true);
      setSearchError(null);
      try {
        const res = await api.market.search(query.trim(), 15, activeCurrency, {
          sector: selectedSector || undefined,
          index: selectedIndex || undefined,
          cap_bucket: selectedCap || undefined,
        });
        if (cancelled) return;
        setResults(res.results || []);
        setIsOpen(true);
      } catch (err) {
        if (cancelled) return;
        setSearchError(err instanceof Error ? err.message : "Search failed.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 200);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [hasCriteria, query, selectedSector, selectedIndex, selectedCap, activeCurrency]);

  return (
    <div className="relative w-full space-y-2" ref={dropdownRef}>
      {/* Search Bar Input */}
      <div className="relative">
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => {
            if (visibleResults.length > 0 || hasCriteria) {
              setIsOpen(true);
            }
          }}
          placeholder="Search NSE/US stocks by symbol, name or ISIN (e.g. RELIANCE, SPY)"
          className="w-full pl-9 pr-9 py-2 text-xs rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
        />
        {loading && (
          <Loader2 className="absolute right-3 top-2.5 w-4 h-4 text-indigo-500 animate-spin" />
        )}
      </div>

      {/* Filter Chips Bar */}
      <div className="flex flex-wrap items-center gap-1.5 pt-0.5 text-[11px]">
        <span className="text-slate-400 text-[10px] font-semibold uppercase tracking-wider mr-1">
          Quick Filters:
        </span>

        {/* Index Chips */}
        {POPULAR_INDEX_CHIPS.map((idx) => {
          const isSelected = selectedIndex === idx;
          return (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setSelectedIndex(isSelected ? null : idx);
                setIsOpen(true);
              }}
              className={`px-2 py-0.5 rounded-full border transition-all text-[10px] font-medium flex items-center gap-1 ${
                isSelected
                  ? "bg-indigo-600 border-indigo-600 text-white shadow-sm"
                  : "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-indigo-400"
              }`}
            >
              <Layers className="w-2.5 h-2.5" />
              {idx}
            </button>
          );
        })}

        {/* Sector Chips */}
        {POPULAR_SECTOR_CHIPS.map((sec) => {
          const isSelected = selectedSector === sec;
          return (
            <button
              key={sec}
              type="button"
              onClick={() => {
                setSelectedSector(isSelected ? null : sec);
                setIsOpen(true);
              }}
              className={`px-2 py-0.5 rounded-full border transition-all text-[10px] font-medium flex items-center gap-1 ${
                isSelected
                  ? "bg-emerald-600 border-emerald-600 text-white shadow-sm"
                  : "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-emerald-400"
              }`}
            >
              <Tag className="w-2.5 h-2.5" />
              {sec}
            </button>
          );
        })}

        {/* Cap Bucket Chips */}
        {CAP_CHIPS.map((cap) => {
          const isSelected = selectedCap === cap;
          return (
            <button
              key={cap}
              type="button"
              onClick={() => {
                setSelectedCap(isSelected ? null : cap);
                setIsOpen(true);
              }}
              className={`px-2 py-0.5 rounded-full border transition-all text-[10px] font-medium ${
                isSelected
                  ? "bg-amber-600 border-amber-600 text-white shadow-sm"
                  : "bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-amber-400"
              }`}
            >
              {cap}
            </button>
          );
        })}

        {(selectedSector || selectedIndex || selectedCap || query) && (
          <button
            type="button"
            onClick={() => {
              setSelectedSector(null);
              setSelectedIndex(null);
              setSelectedCap(null);
              setQuery("");
              setResults([]);
              setSearchError(null);
            }}
            className="text-[10px] text-slate-400 hover:text-rose-500 underline ml-1"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Dropdown Results Box */}
      {searchError && (
        <p role="alert" className="text-[11px] text-red-600 dark:text-red-400">
          Search unavailable: {searchError}
        </p>
      )}

      {isOpen && visibleResults.length > 0 && (
        <div className="absolute left-0 right-0 z-30 mt-1 max-h-72 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl divide-y divide-slate-100 dark:divide-slate-800">
          <div className="p-2 text-[10px] font-semibold text-slate-400 bg-slate-50 dark:bg-slate-800/50 uppercase tracking-wider flex justify-between items-center">
            <span>Matching Instruments ({visibleResults.length})</span>
            <span className="text-[9px] text-slate-500 font-normal">Click to add to portfolio</span>
          </div>

          {visibleResults.map((item) => {
            const isAlreadyAdded = disabledSymbols.includes(item.symbol);
            return (
              <div
                key={item.symbol}
                className={`p-2.5 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/70 transition-colors ${
                  isAlreadyAdded ? "opacity-60 bg-slate-50/40 dark:bg-slate-800/20" : "cursor-pointer"
                }`}
                onClick={() => {
                  if (!isAlreadyAdded) {
                    onSelectSymbol(item.symbol, item.name, item.currency);
                    setIsOpen(false);
                    setQuery("");
                  }
                }}
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xs text-slate-900 dark:text-slate-100">
                      {item.symbol}
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-semibold ${
                        item.currency === "INR"
                          ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300"
                          : "bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300"
                      }`}
                    >
                      {item.currency}
                    </span>
                    <span className="text-[10px] text-slate-400">{item.exchange}</span>
                    {item.is_cached && (
                      <span className="text-[9px] px-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">
                        Cached
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-600 dark:text-slate-300 truncate max-w-sm">
                    {item.name}
                  </div>
                </div>

                <div>
                  {isAlreadyAdded ? (
                    <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                      <Check className="w-3 h-3" /> Added
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 dark:hover:bg-indigo-900 transition-colors flex items-center gap-1"
                    >
                      <Plus className="w-3 h-3" /> Add
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
