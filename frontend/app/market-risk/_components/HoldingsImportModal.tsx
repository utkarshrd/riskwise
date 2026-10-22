"use client";

import { useState, useRef, type DragEvent, type ChangeEvent } from "react";
import {
  Upload,
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  X,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Sparkles,
} from "lucide-react";
import { Alert, Badge, Stat } from "@/components/ui";
import type { PortfolioImportResponse } from "@/lib/api";

interface HoldingsImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  isUploading: boolean;
  result: PortfolioImportResponse | null;
  error: string | null;
  fileName: string | null;
  onUploadFile: (file: File) => Promise<void>;
  onReset: () => void;
  onApplyHoldings: (
    holdings: PortfolioImportResponse["holdings"],
    inferredCurrency?: string | null,
    totalValue?: number
  ) => void;
}

export default function HoldingsImportModal({
  isOpen,
  onClose,
  isUploading,
  result,
  error,
  fileName,
  onUploadFile,
  onReset,
  onApplyHoldings,
}: HoldingsImportModalProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await onUploadFile(file);
    }
  };

  const handleFileChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await onUploadFile(file);
    }
  };

  const handleApply = () => {
    if (!result || result.holdings.length === 0) return;
    onApplyHoldings(result.holdings, result.inferred_currency, result.total_value);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Import Broker Holdings</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Upload CSV export from Zerodha Kite, Groww, or canonical format with auto-resolved weights
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Upload Dropzone (shown when no result yet) */}
          {!result && !isUploading && (
            <div className="space-y-4">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative flex flex-col items-center justify-center p-8 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
                  isDragging
                    ? "border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20"
                    : "border-slate-200 dark:border-slate-700 hover:border-indigo-400 dark:hover:border-indigo-500 bg-slate-50/50 dark:bg-slate-800/20"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="p-3.5 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 mb-3 shadow-inner">
                  <FileText className="w-7 h-7" />
                </div>
                <p className="text-sm font-medium text-slate-800 dark:text-slate-200 mb-1">
                  Click to browse or drag and drop your broker CSV here
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Maximum file size: 1 MB • Up to 500 rows • Comma, semicolon, or tab delimited
                </p>
              </div>

              {/* Supported Brokers Guide */}
              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 space-y-2">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  <span>Supported Column Formats</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 text-xs text-slate-600 dark:text-slate-400">
                  <div className="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                    <span className="font-semibold text-slate-900 dark:text-white block mb-0.5">Zerodha Kite</span>
                    <span className="font-mono text-[11px] text-slate-500 block truncate">
                      Instrument, Qty., Avg. cost, LTP
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                    <span className="font-semibold text-slate-900 dark:text-white block mb-0.5">Groww</span>
                    <span className="font-mono text-[11px] text-slate-500 block truncate">
                      Stock Name, ISIN, Quantity, Avg price
                    </span>
                  </div>
                  <div className="p-2.5 rounded bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700">
                    <span className="font-semibold text-slate-900 dark:text-white block mb-0.5">Canonical</span>
                    <span className="font-mono text-[11px] text-slate-500 block truncate">
                      symbol, quantity, avg_price
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Loading State */}
          {isUploading && (
            <div className="py-16 flex flex-col items-center justify-center space-y-4">
              <div className="w-12 h-12 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <div className="text-center">
                <p className="text-sm font-medium text-slate-900 dark:text-white">
                  Reading {fileName || "CSV file"} and fetching latest prices...
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Resolving ISINs, official symbols, and computing portfolio weights
                </p>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <Alert
              tone="error"
              title="Import Failed"
              action={
                <button
                  type="button"
                  onClick={onReset}
                  className="px-2.5 py-1 text-xs font-medium rounded bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 hover:bg-rose-200 transition"
                >
                  Try Again
                </button>
              }
            >
              <span>{error}</span>
            </Alert>
          )}

          {/* Results View */}
          {result && (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Stat
                  label="Imported Assets"
                  value={result.rows.imported}
                  hint={`${result.rows.total} total rows in CSV`}
                />
                <Stat
                  label="Total Value"
                  value={
                    result.total_value > 0
                      ? `${result.inferred_currency || "INR"} ${result.total_value.toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}`
                      : "N/A"
                  }
                  hint={`${(result.holdings.reduce((sum, h) => sum + h.weight, 0) * 100).toFixed(1)}% total weight`}
                />
                <Stat
                  label="Merged Duplicates"
                  value={result.rows.merged}
                  hint={result.rows.merged > 0 ? "Weighted avg prices" : "None"}
                />
                <Stat
                  label="Validation Errors"
                  value={result.rows.errors}
                  hint={result.rows.errors > 0 ? "Excluded from import" : "Clean import"}
                />
              </div>

              {/* Header Mapping & Currency Badge */}
              <div className="flex flex-wrap items-center justify-between gap-2 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/40 text-xs text-slate-600 dark:text-slate-400">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">Header Mapping:</span>
                  {Object.entries(result.header_mapping).map(([canonical, header]) => (
                    <Badge key={canonical} tone="neutral">
                      <span className="font-mono text-slate-500">{canonical}</span>
                      <ArrowRight className="w-2.5 h-2.5 mx-1 inline" />
                      <span className="font-medium text-slate-800 dark:text-slate-200">{header}</span>
                    </Badge>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <span>Currency:</span>
                  <Badge tone={result.inferred_currency ? "green" : "amber"}>
                    {result.inferred_currency ? `${result.inferred_currency} (Single)` : "Mixed (USD/INR)"}
                  </Badge>
                </div>
              </div>

              {/* Warnings (if any) */}
              {result.warnings.length > 0 && (
                <div className="p-3 rounded-lg bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 space-y-1">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 dark:text-amber-300">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>Merge Notices</span>
                  </div>
                  {result.warnings.map((w, idx) => (
                    <p key={idx} className="text-xs text-amber-700 dark:text-amber-400 pl-5">
                      • {w}
                    </p>
                  ))}
                </div>
              )}

              {/* Imported Holdings Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-900 dark:text-white uppercase tracking-wider">
                    Ready to Import ({result.holdings.length} Holdings)
                  </h3>
                  <span className="text-[11px] text-slate-500">Prices sourced from verified platform market data</span>
                </div>

                <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-x-auto max-h-72">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-800/80 sticky top-0 border-b border-slate-200 dark:border-slate-800 font-semibold text-slate-600 dark:text-slate-300">
                      <tr>
                        <th className="py-2.5 px-3">Symbol</th>
                        <th className="py-2.5 px-3">Name</th>
                        <th className="py-2.5 px-3 text-right">Quantity</th>
                        <th className="py-2.5 px-3 text-right">Latest Price</th>
                        <th className="py-2.5 px-3 text-right">Position Value</th>
                        <th className="py-2.5 px-3 text-right">Weight</th>
                        <th className="py-2.5 px-3 text-right">Avg Buy Cost</th>
                        <th className="py-2.5 px-3 text-right">Unrealized P&L</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                      {result.holdings.map((h) => (
                        <tr key={h.symbol} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                          <td className="py-2 px-3 font-semibold text-slate-900 dark:text-white">
                            {h.symbol}
                            {h.merged_count > 1 && (
                              <span
                                className="ml-1.5 px-1 py-0.2 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                                title={`Merged from ${h.merged_count} rows`}
                              >
                                {h.merged_count}x
                              </span>
                            )}
                          </td>
                          <td className="py-2 px-3 font-sans text-slate-600 dark:text-slate-400 truncate max-w-[140px]">
                            {h.name}
                          </td>
                          <td className="py-2 px-3 text-right text-slate-800 dark:text-slate-200">{h.quantity}</td>
                          <td className="py-2 px-3 text-right text-slate-800 dark:text-slate-200">
                            {h.latest_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="py-2 px-3 text-right font-medium text-slate-900 dark:text-white">
                            {h.position_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="py-2 px-3 text-right font-semibold text-indigo-600 dark:text-indigo-400">
                            {(h.weight * 100).toFixed(2)}%
                          </td>
                          <td className="py-2 px-3 text-right text-slate-500">
                            {h.avg_price != null ? h.avg_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—"}
                          </td>
                          <td className="py-2 px-3 text-right">
                            {h.unrealized_pnl != null && h.unrealized_pnl_pct != null ? (
                              <span
                                className={`inline-flex items-center gap-0.5 font-semibold ${
                                  h.unrealized_pnl >= 0
                                    ? "text-emerald-600 dark:text-emerald-400"
                                    : "text-rose-600 dark:text-rose-400"
                                }`}
                              >
                                {h.unrealized_pnl >= 0 ? (
                                  <TrendingUp className="w-3 h-3" />
                                ) : (
                                  <TrendingDown className="w-3 h-3" />
                                )}
                                {h.unrealized_pnl >= 0 ? "+" : ""}
                                {h.unrealized_pnl_pct.toFixed(2)}%
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Rejected Rows / Errors Section */}
              {result.errors.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-700 dark:text-rose-400">
                    <XCircle className="w-4 h-4" />
                    <span>Rejected Rows ({result.errors.length} not imported)</span>
                  </div>

                  <div className="border border-rose-200 dark:border-rose-900/50 rounded-lg overflow-x-auto max-h-48 bg-rose-50/30 dark:bg-rose-950/10">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-rose-100/50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-300 font-semibold sticky top-0">
                        <tr>
                          <th className="py-2 px-3">Row #</th>
                          <th className="py-2 px-3">Field</th>
                          <th className="py-2 px-3">Offending Value</th>
                          <th className="py-2 px-3">Reason & Suggestions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-rose-100 dark:divide-rose-900/40 font-mono text-[11px]">
                        {result.errors.map((err, i) => (
                          <tr key={i} className="hover:bg-rose-100/20">
                            <td className="py-1.5 px-3 font-semibold text-rose-700 dark:text-rose-400">
                              Row {err.row}
                            </td>
                            <td className="py-1.5 px-3 text-slate-700 dark:text-slate-300 font-sans">{err.field}</td>
                            <td className="py-1.5 px-3 text-rose-900 dark:text-rose-200 max-w-[120px] truncate">
                              {err.offending_value ? String(err.offending_value) : "—"}
                            </td>
                            <td className="py-1.5 px-3 font-sans text-slate-600 dark:text-slate-400">
                              <span>{err.message}</span>
                              {err.suggestions && err.suggestions.length > 0 && (
                                <div className="mt-1 flex items-center gap-1">
                                  <span className="text-[10px] text-slate-500">Suggestions:</span>
                                  {err.suggestions.map((s) => (
                                    <span
                                      key={s.symbol}
                                      className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-[10px] font-mono font-medium text-slate-800 dark:text-slate-200"
                                      title={s.name}
                                    >
                                      {s.symbol}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <div>
            {result && (
              <button
                type="button"
                onClick={onReset}
                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
              >
                Upload another file
              </button>
            )}
          </div>
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              Cancel
            </button>
            {result && (
              <button
                type="button"
                onClick={handleApply}
                disabled={result.holdings.length === 0}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>Use These Holdings ({result.holdings.length})</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
