"use client";

import { useState } from "react";
import { Activity, Zap, Info, TrendingDown, TrendingUp } from "lucide-react";
import { api, StressTestResponse } from "@/lib/api";

function MetricCard({
  label, baseline, stressed, unit = "", format = "number"
}: {
  label: string;
  baseline: number | null;
  stressed: number | null;
  unit?: string;
  format?: "number" | "percent" | "months";
}) {
  const bVal = baseline ?? 0;
  const sVal = stressed ?? 0;
  const delta = sVal - bVal;

  const fmt = (v: number | null) => {
    if (v == null) return "N/A";
    if (format === "percent") return `${(v * 100).toFixed(1)}%`;
    if (format === "months") return `${v.toFixed(1)} mo`;
    return v.toLocaleString("en-IN", { maximumFractionDigits: 0 }) + (unit ? ` ${unit}` : "");
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4">
      <div className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-2">{label}</div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-[10px] text-slate-400 mb-0.5">Baseline</div>
          <div className="text-base font-bold text-slate-900 dark:text-slate-100">{fmt(baseline)}</div>
        </div>
        <div>
          <div className="text-[10px] text-slate-400 mb-0.5">Stressed</div>
          <div className="flex items-center gap-1">
            <div className={`text-base font-bold ${sVal < bVal ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
              {fmt(stressed)}
            </div>
            {baseline != null && stressed != null && (
              delta > 0
                ? <TrendingUp className="w-3.5 h-3.5 text-green-500" />
                : <TrendingDown className="w-3.5 h-3.5 text-red-500" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function StressTestPage() {
  // Inputs
  const [income, setIncome] = useState("80000");
  const [essential, setEssential] = useState("35000");
  const [discretionary, setDiscretionary] = useState("15000");
  const [emis, setEmis] = useState("12000");
  const [savings, setSavings] = useState("150000");
  const [loanPrincipal, setLoanPrincipal] = useState("0");
  const [loanRate, setLoanRate] = useState("0.105");
  const [loanTenure, setLoanTenure] = useState("0");
  // Scenario
  const [incomeReduction, setIncomeReduction] = useState("20");
  const [essentialSurge, setEssentialSurge] = useState("10");
  const [discretionarySurge, setDiscretionarySurge] = useState("0");
  const [rateHike, setRateHike] = useState("0");

  const [result, setResult] = useState<StressTestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStressTest() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.finance.stressTest({
        monthly_income: parseFloat(income),
        essential_expenses: parseFloat(essential),
        discretionary_expenses: parseFloat(discretionary),
        existing_emis: parseFloat(emis),
        liquid_savings: parseFloat(savings),
        proposed_loan_principal: parseFloat(loanPrincipal) || 0,
        proposed_loan_interest_rate: parseFloat(loanRate) || 0,
        proposed_loan_tenure_months: parseInt(loanTenure) || 0,
        scenario: {
          income_reduction_pct: parseFloat(incomeReduction) || 0,
          essential_expense_surge_pct: parseFloat(essentialSurge) || 0,
          discretionary_expense_surge_pct: parseFloat(discretionarySurge) || 0,
          interest_rate_hike_pct: parseFloat(rateHike) || 0,
        },
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  const assessmentColor = (assessment: string) => {
    if (assessment.startsWith("CRITICAL")) return "text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800";
    if (assessment.startsWith("VULNERABLE")) return "text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800";
    if (assessment.startsWith("OVERBURDENED")) return "text-orange-700 dark:text-orange-400 bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-800";
    return "text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800";
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto animate-fade-in">
      <div>
        <div className="flex items-center gap-2 text-xs font-medium text-emerald-600 dark:text-emerald-400 mb-1">
          <span className="px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800">
            Milestone 3 · Deterministic Cash-Flow Engine
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Personal Financial Stress Testing
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Model adverse income / expense shocks on household finances. Computes baseline and stressed surplus, debt-to-income ratio, and emergency runway.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Form */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-500" />
              Monthly Household Finances
            </h2>

            {[
              { label: "Monthly Income (₹)", value: income, set: setIncome },
              { label: "Essential Expenses (₹)", value: essential, set: setEssential },
              { label: "Discretionary Expenses (₹)", value: discretionary, set: setDiscretionary },
              { label: "Existing EMIs (₹)", value: emis, set: setEmis },
              { label: "Liquid Savings (₹)", value: savings, set: setSavings },
            ].map(({ label, value, set }) => (
              <div key={label} className="mb-3">
                <label className="text-[11px] font-medium text-slate-500 dark:text-slate-400 block mb-0.5">{label}</label>
                <input
                  type="number"
                  value={value}
                  onChange={(e) => set(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                />
              </div>
            ))}

            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
              <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-3 uppercase tracking-wider">
                Proposed New Loan (optional)
              </div>
              {[
                { label: "Loan Principal (₹)", value: loanPrincipal, set: setLoanPrincipal },
                { label: "Annual Rate (e.g. 0.105)", value: loanRate, set: setLoanRate },
                { label: "Tenure (months)", value: loanTenure, set: setLoanTenure },
              ].map(({ label, value, set }) => (
                <div key={label} className="mb-3">
                  <label className="text-[11px] font-medium text-slate-500 dark:text-slate-400 block mb-0.5">{label}</label>
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => set(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                  />
                </div>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
              <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-3 uppercase tracking-wider">
                Adverse Stress Scenario
              </div>
              {[
                { label: "Income Reduction %", value: incomeReduction, set: setIncomeReduction },
                { label: "Essential Expense Surge %", value: essentialSurge, set: setEssentialSurge },
                { label: "Discretionary Surge %", value: discretionarySurge, set: setDiscretionarySurge },
                { label: "Interest Rate Hike (pp)", value: rateHike, set: setRateHike },
              ].map(({ label, value, set }) => (
                <div key={label} className="mb-3">
                  <label className="text-[11px] font-medium text-slate-500 dark:text-slate-400 block mb-0.5">{label}</label>
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => set(e.target.value)}
                    className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                  />
                </div>
              ))}
            </div>

            <button
              onClick={handleStressTest}
              disabled={loading}
              className="mt-5 w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg flex items-center justify-center gap-2 transition"
            >
              {loading ? <span className="animate-spin border-2 border-white/30 border-t-white rounded-full w-4 h-4" /> : <Zap className="w-4 h-4" />}
              {loading ? "Running..." : "Run Stress Test"}
            </button>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-5">
          {error && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">{error}</div>
          )}

          {result && (
            <>
              {/* Risk Assessment */}
              <div className={`p-4 rounded-xl border text-sm font-medium ${assessmentColor(result.risk_assessment)}`}>
                <Info className="w-4 h-4 inline mr-2" />
                {result.risk_assessment}
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <MetricCard
                  label="Monthly Surplus (₹)"
                  baseline={result.baseline_surplus}
                  stressed={result.stressed_surplus}
                  format="number"
                />
                <MetricCard
                  label="EMI-to-Income Ratio"
                  baseline={result.baseline_emi_to_income_ratio}
                  stressed={result.stressed_emi_to_income_ratio}
                  format="percent"
                />
                <MetricCard
                  label="Emergency Runway"
                  baseline={result.baseline_runway_months}
                  stressed={result.stressed_runway_months}
                  format="months"
                />
                <MetricCard
                  label="Proposed EMI (₹)"
                  baseline={result.proposed_emi}
                  stressed={result.stressed_proposed_emi}
                  format="number"
                />
              </div>

              {/* Waterfall Summary Table */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
                <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-4">Cash Flow Summary</h2>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-100 dark:border-slate-800">
                      <th className="text-left py-2 font-medium">Item</th>
                      <th className="text-right py-2 font-medium">Baseline</th>
                      <th className="text-right py-2 font-medium">Stressed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {[
                      ["Income", result.baseline_income, result.stressed_income],
                      ["Essential Expenses", result.baseline_essential_expenses, result.stressed_essential_expenses],
                      ["Discretionary Expenses", result.baseline_discretionary_expenses, result.stressed_discretionary_expenses],
                      ["Existing EMIs", result.baseline_existing_emis, result.stressed_existing_emis],
                      ["Proposed EMI", result.proposed_emi, result.stressed_proposed_emi],
                      ["Net Surplus", result.baseline_surplus, result.stressed_surplus],
                    ].map(([label, base, stress]) => (
                      <tr key={label as string}>
                        <td className="py-2 text-slate-600 dark:text-slate-400">{label}</td>
                        <td className="py-2 text-right font-mono text-slate-900 dark:text-slate-100">
                          {typeof base === "number" ? `₹${base.toLocaleString()}` : base}
                        </td>
                        <td className={`py-2 text-right font-mono ${
                          label === "Income" || label === "Net Surplus"
                            ? (stress as number) < (base as number) ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"
                            : (stress as number) > (base as number) ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"
                        }`}>
                          {typeof stress === "number" ? `₹${stress.toLocaleString()}` : stress}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-64 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 text-slate-400 text-sm gap-3">
              <Activity className="w-10 h-10 opacity-40" />
              <p>Configure household finances and stress scenario, then click <strong>Run Stress Test</strong></p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
