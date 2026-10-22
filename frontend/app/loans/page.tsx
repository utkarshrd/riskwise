"use client";

import { useState } from "react";
import { Calculator, Zap, DollarSign } from "lucide-react";
import { api, EMIResponse } from "@/lib/api";

export default function LoanAffordabilityPage() {
  const [principal, setPrincipal] = useState("500000");
  const [rate, setRate] = useState("10.5");
  const [tenure, setTenure] = useState("36");
  const [result, setResult] = useState<EMIResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSchedule, setShowSchedule] = useState(false);

  async function handleCalculate() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.finance.emi({
        principal: parseFloat(principal),
        annual_interest_rate: parseFloat(rate) / 100,
        tenure_months: parseInt(tenure),
        include_schedule: true,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  // Sensitivity: vary rate from -3pp to +3pp
  const sensitivityRates = result
    ? [-3, -2, -1, 0, 1, 2, 3].map((delta) => {
        const r = Math.max(0, parseFloat(rate) + delta) / 100;
        const monthly_rate = r / 12;
        const n = result.tenure_months;
        let emi: number;
        if (monthly_rate === 0) {
          emi = result.principal / n;
        } else {
          const factor = Math.pow(1 + monthly_rate, n);
          emi = (result.principal * monthly_rate * factor) / (factor - 1);
        }
        return { delta, emi: Math.round(emi), rate: parseFloat(rate) + delta };
      })
    : [];

  return (
    <div className="space-y-8 max-w-5xl mx-auto animate-fade-in">
      <div>
        <div className="flex items-center gap-2 text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
          <span className="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800">
            Reducing-balance EMI engine
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Loan Affordability &amp; EMI Modeling
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Exact reducing-balance amortization: <code className="bg-slate-100 dark:bg-slate-800 px-1 rounded font-mono">EMI = P · r · (1+r)^n / ((1+r)^n - 1)</code>
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-4 flex items-center gap-2">
              <Calculator className="w-4 h-4 text-blue-500" />
              Loan Parameters
            </h2>
            {[
              { label: "Principal Amount (₹)", value: principal, set: setPrincipal, min: "1000" },
              { label: "Annual Interest Rate (%)", value: rate, set: setRate, step: "0.1", min: "0" },
              { label: "Tenure (months)", value: tenure, set: setTenure, min: "1", max: "360" },
            ].map(({ label, value, set, step, min, max }) => (
              <div key={label} className="mb-4">
                <label className="text-[11px] font-medium text-slate-500 dark:text-slate-400 block mb-1">{label}</label>
                <input
                  type="number"
                  value={value}
                  onChange={(e) => set(e.target.value)}
                  step={step}
                  min={min}
                  max={max}
                  className="w-full px-2.5 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                />
              </div>
            ))}
            <button
              onClick={handleCalculate}
              disabled={loading}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg flex items-center justify-center gap-2 transition"
            >
              {loading ? <span className="animate-spin border-2 border-white/30 border-t-white rounded-full w-4 h-4" /> : <Zap className="w-4 h-4" />}
              {loading ? "Calculating..." : "Calculate EMI"}
            </button>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-5">
          {error && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          {result && (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: "Monthly EMI", value: `₹${result.monthly_emi.toLocaleString()}`, sub: "Reducing balance", color: "text-blue-600 dark:text-blue-400" },
                  { label: "Total Interest", value: `₹${result.total_interest.toLocaleString()}`, sub: `${((result.total_interest / result.principal) * 100).toFixed(1)}% of principal`, color: "text-amber-600 dark:text-amber-400" },
                  { label: "Total Repayment", value: `₹${result.total_payment.toLocaleString()}`, sub: `Over ${result.tenure_months} months`, color: "text-slate-900 dark:text-slate-100" },
                ].map(({ label, value, sub, color }) => (
                  <div key={label} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-4 text-center">
                    <div className="text-[10px] font-medium text-slate-500 mb-1">{label}</div>
                    <div className={`text-xl font-bold ${color}`}>{value}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{sub}</div>
                  </div>
                ))}
              </div>

              {/* Principal vs Interest donut-style bar */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">Principal vs Interest Breakdown</h3>
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex-1 h-4 rounded-full overflow-hidden bg-slate-100 dark:bg-slate-800 flex">
                    <div
                      className="h-full bg-blue-500 transition-all duration-700"
                      style={{ width: `${(result.principal / result.total_payment) * 100}%` }}
                    />
                    <div
                      className="h-full bg-amber-400 transition-all duration-700"
                      style={{ width: `${(result.total_interest / result.total_payment) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="flex gap-4 text-xs">
                  <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-blue-500" /> <span className="text-slate-600 dark:text-slate-400">Principal: ₹{result.principal.toLocaleString()}</span></div>
                  <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-sm bg-amber-400" /> <span className="text-slate-600 dark:text-slate-400">Interest: ₹{result.total_interest.toLocaleString()}</span></div>
                </div>
              </div>

              {/* Rate Sensitivity Table */}
              <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">Interest Rate Sensitivity</h3>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-100 dark:border-slate-800">
                      <th className="text-left py-2">Rate Scenario</th>
                      <th className="text-right py-2">Annual Rate</th>
                      <th className="text-right py-2">Monthly EMI</th>
                      <th className="text-right py-2">Delta vs Base</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                    {sensitivityRates.map(({ delta, emi, rate: r }) => (
                      <tr key={delta} className={delta === 0 ? "bg-blue-50/50 dark:bg-blue-950/20 font-semibold" : ""}>
                        <td className="py-2 text-slate-600 dark:text-slate-400">
                          {delta === 0 ? "Base" : delta > 0 ? `+${delta}pp hike` : `${delta}pp cut`}
                        </td>
                        <td className="py-2 text-right">{r.toFixed(1)}%</td>
                        <td className="py-2 text-right font-mono text-slate-900 dark:text-slate-100">₹{emi.toLocaleString()}</td>
                        <td className={`py-2 text-right font-mono ${delta === 0 ? "text-slate-400" : delta > 0 ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400"}`}>
                          {delta === 0 ? "—" : `${(emi - sensitivityRates[3].emi) > 0 ? "+" : ""}₹${(emi - sensitivityRates[3].emi).toLocaleString()}`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Amortization Schedule */}
              {result.amortization_schedule.length > 0 && (
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Amortization Schedule</h3>
                    <button
                      onClick={() => setShowSchedule(!showSchedule)}
                      className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      {showSchedule ? "Hide" : "Show all"} {result.tenure_months} months
                    </button>
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0 bg-white dark:bg-slate-900">
                        <tr className="text-slate-400 border-b border-slate-100 dark:border-slate-800">
                          <th className="text-left py-1.5">Month</th>
                          <th className="text-right py-1.5">Payment</th>
                          <th className="text-right py-1.5">Principal</th>
                          <th className="text-right py-1.5">Interest</th>
                          <th className="text-right py-1.5">Balance</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50 dark:divide-slate-800">
                        {(showSchedule ? result.amortization_schedule : result.amortization_schedule.slice(0, 6)).map((row) => (
                          <tr key={row.month}>
                            <td className="py-1.5 text-slate-600 dark:text-slate-400">{row.month}</td>
                            <td className="py-1.5 text-right font-mono">₹{row.payment.toLocaleString()}</td>
                            <td className="py-1.5 text-right font-mono text-blue-600 dark:text-blue-400">₹{row.principal_payment.toLocaleString()}</td>
                            <td className="py-1.5 text-right font-mono text-amber-600 dark:text-amber-400">₹{row.interest_payment.toLocaleString()}</td>
                            <td className="py-1.5 text-right font-mono text-slate-700 dark:text-slate-300">₹{row.remaining_balance.toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}

          {!result && !loading && (
            <div className="flex flex-col items-center justify-center h-64 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 text-slate-400 text-sm gap-3">
              <DollarSign className="w-10 h-10 opacity-40" />
              <p>Enter loan parameters and click <strong>Calculate EMI</strong></p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
