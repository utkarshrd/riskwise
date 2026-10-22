"use client";

import { useState } from "react";
import { Award, CheckCircle2, Activity, Sparkles, Loader2 } from "lucide-react";
import { api, FxMode, VaRCompareResponse, VaRModelComparisonItem } from "@/lib/api";

interface VaRModelComparisonProps {
  holdings: Array<{ symbol: string; weight: number; position_value?: number }>;
  currency: string;
  confidenceLevel: number;
  lookbackWindow: number;
  fxMode?: FxMode;
  onSelectMethod: (method: string) => void;
  activeMethod: string;
}

export default function VaRModelComparison({
  holdings,
  currency,
  confidenceLevel,
  lookbackWindow,
  fxMode = "strict",
  onSelectMethod,
  activeMethod,
}: VaRModelComparisonProps) {
  const [loading, setLoading] = useState(false);
  const [comparison, setComparison] = useState<VaRCompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.market.compareVar({
        holdings: holdings.map((h) => ({
          symbol: h.symbol,
          weight: h.weight,
          position_value: h.position_value,
        })),
        portfolio_name: "Comparative Evaluation",
        currency,
        confidence_level: confidenceLevel,
        lookback_window: lookbackWindow,
        methods: ["historical", "parametric", "student_t", "cornish_fisher", "ewma"],
        fx_mode: fxMode,
      });
      setComparison(res);
    } catch (err: unknown) {
      console.error("Comparison error:", err);
      const msg = err instanceof Error ? err.message : "Failed to run model comparison.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
      {/* Header & Run Comparison Button */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-3">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-500" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Multi-Model Regulatory Benchmark & Leaderboard
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Simultaneously evaluates 5 candidate VaR models on the exact same historical window and recommends the optimal model under BCBS standards.
          </p>
        </div>

        <button
          type="button"
          onClick={handleRunComparison}
          disabled={loading || holdings.length === 0}
          className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50 shrink-0"
        >
          {loading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Activity className="w-3.5 h-3.5" />
          )}
          {loading ? "Evaluating Models..." : "Run Multi-Model Comparison"}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-700 dark:text-rose-300">
          {error}
        </div>
      )}

      {!comparison && !loading && !error && (
        <div className="p-6 rounded-xl border border-dashed border-slate-200 dark:border-slate-800 text-center space-y-2">
          <div className="text-xs text-slate-500 dark:text-slate-400">
            Click <strong>Run Multi-Model Comparison</strong> to rank Historical, Parametric, Student-t, Cornish-Fisher, and EWMA models side-by-side.
          </div>
        </div>
      )}

      {comparison && (
        <div className="space-y-4">
          {/* Plain English Recommendation Banner */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-50 to-emerald-50 dark:from-indigo-950/40 dark:to-emerald-950/40 border border-indigo-200 dark:border-indigo-800 space-y-2">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-indigo-600 text-white">
                <Award className="w-4 h-4" />
              </div>
              <div className="font-semibold text-xs text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <span>Model Recommendation:</span>
                <span className="font-mono px-2 py-0.5 rounded bg-indigo-600 text-white font-bold uppercase">
                  {comparison.recommended_method.replace("_", " ")}
                </span>
              </div>
            </div>
            <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 pl-8">
              {comparison.recommendation_reason}
            </p>
          </div>

          {/* Leaderboard Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800 font-medium">
                <tr>
                  <th className="py-2.5 px-3">Rank / Method</th>
                  <th className="py-2.5 px-3 text-center">Exceptions</th>
                  <th className="py-2.5 px-3 text-center">Exception Rate</th>
                  <th className="py-2.5 px-3 text-center">Basel Zone</th>
                  <th className="py-2.5 px-3 text-center">Multiplier</th>
                  <th className="py-2.5 px-3 text-center">Kupiec POF</th>
                  <th className="py-2.5 px-3 text-center">Christoffersen CC</th>
                  <th className="py-2.5 px-3 text-center">Penalty Score</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                {comparison.models.map((m: VaRModelComparisonItem, idx: number) => {
                  const isRecommended = m.method === comparison.recommended_method;
                  const isCurrentActive = m.method === activeMethod;

                  return (
                    <tr
                      key={m.method}
                      className={`hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors ${
                        isRecommended ? "bg-indigo-50/30 dark:bg-indigo-950/20 font-semibold" : ""
                      }`}
                    >
                      <td className="py-2.5 px-3">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] flex items-center justify-center font-bold">
                            {idx + 1}
                          </span>
                          <span className="capitalize text-slate-900 dark:text-slate-100">
                            {m.method.replace("_", " ")}
                          </span>
                          {isRecommended && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 font-bold">
                              Best
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-2.5 px-3 text-center font-bold">
                        {m.exceptions} <span className="text-[10px] text-slate-400 font-normal">/ {m.expected_exceptions.toFixed(1)} exp</span>
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        {(m.exception_rate * 100).toFixed(2)}%
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            m.basel_zone === "GREEN"
                              ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800"
                              : m.basel_zone === "YELLOW"
                              ? "bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800"
                              : "bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-800"
                          }`}
                        >
                          {m.basel_zone}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        {m.basel_capital_multiplier.toFixed(2)}x
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`text-[10px] ${
                            m.kupiec_test_passed
                              ? "text-emerald-600 dark:text-emerald-400 font-semibold"
                              : "text-red-600 dark:text-red-400 font-bold"
                          }`}
                        >
                          {m.kupiec_test_passed ? "Pass" : "Fail"} (p={m.kupiec_p_value != null ? m.kupiec_p_value.toFixed(3) : "N/A"})
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <span
                          className={`text-[10px] ${
                            m.christoffersen_cc_test_passed
                              ? "text-emerald-600 dark:text-emerald-400 font-semibold"
                              : "text-red-600 dark:text-red-400 font-bold"
                          }`}
                        >
                          {m.christoffersen_cc_test_passed ? "Pass" : "Fail"} (p={m.christoffersen_cc_p_value != null ? m.christoffersen_cc_p_value.toFixed(3) : "N/A"})
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-center font-bold text-slate-700 dark:text-slate-300">
                        {m.score.toFixed(1)}
                      </td>

                      <td className="py-2.5 px-3 text-right">
                        {isCurrentActive ? (
                          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center justify-end gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Active
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => onSelectMethod(m.method)}
                            className="px-2 py-1 rounded-lg text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 hover:bg-indigo-600 hover:text-white transition-colors"
                          >
                            Apply
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
