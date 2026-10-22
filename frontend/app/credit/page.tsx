"use client";

import { useState, useEffect } from "react";
import {
  CreditCard,
  Zap,
  Info,
  AlertTriangle,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  Sliders,
  Sparkles,
  ShieldCheck,
  Building2,
  UserCheck,
  Search,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  api,
  CreditScoreResponse,
  CreditExplainResponse,
  BorrowerProfileSample,
  WhatIfResponse,
} from "@/lib/api";

const DEFAULT_SAMPLE_FEATURES: Record<string, string | number> = {
  pct_tl_open_L6M: 0.15,
  pct_tl_closed_L6M: 0.0,
  Tot_TL_closed_L12M: 0,
  pct_tl_closed_L12M: 0.0,
  Tot_Missed_Pmnt: 0,
  CC_TL: 1,
  Home_TL: 0,
  PL_TL: 1,
  Secured_TL: 0,
  Unsecured_TL: 2,
  Other_TL: 1,
  Age_Oldest_TL: 48,
  Age_Newest_TL: 6,
  time_since_recent_payment: 2,
  max_recent_level_of_deliq: 0,
  num_deliq_6_12mts: 0,
  num_times_60p_dpd: 0,
  num_std_12mts: 12,
  num_sub: 0,
  num_sub_6mts: 0,
  num_sub_12mts: 0,
  num_dbt: 0,
  num_dbt_12mts: 0,
  num_lss: 0,
  recent_level_of_deliq: 0,
  CC_enq_L12m: 1,
  PL_enq_L12m: 1,
  time_since_recent_enq: 4,
  enq_L3m: 1,
  NETMONTHLYINCOME: 42000,
  Time_With_Curr_Empr: 36,
  CC_Flag: 1,
  PL_Flag: 1,
  pct_PL_enq_L6m_of_ever: 0.5,
  pct_CC_enq_L6m_of_ever: 0.5,
  HL_Flag: 0,
  GL_Flag: 0,
  MARITALSTATUS: "Married",
  EDUCATION: "GRADUATE",
  GENDER: "M",
  last_prod_enq2: "PL",
  first_prod_enq2: "CC",
};

const FEATURE_DESCRIPTIONS: Record<string, string> = {
  Tot_Missed_Pmnt: "Total Missed Payments",
  num_times_60p_dpd: "Instances of 60+ Days Past Due",
  NETMONTHLYINCOME: "Net Monthly Income (INR)",
  Time_With_Curr_Empr: "Tenure with Employer (Months)",
  enq_L3m: "Credit Enquiries in Last 3 Months",
  CC_enq_L12m: "Credit Card Enquiries (12M)",
  PL_enq_L12m: "Personal Loan Enquiries (12M)",
  time_since_recent_enq: "Months Since Most Recent Enquiry",
  time_since_recent_payment: "Months Since Most Recent Payment",
  Secured_TL: "Secured Trade Lines (Loans)",
  Unsecured_TL: "Unsecured Trade Lines (Loans)",
  Age_Oldest_TL: "Age of Oldest Trade Line (Months)",
  Age_Newest_TL: "Age of Newest Trade Line (Months)",
  MARITALSTATUS: "Marital Status",
  EDUCATION: "Educational Level",
  GENDER: "Borrower Gender",
};

function getCategoryColor(cat: string): { bg: string; text: string; border: string; bar: string } {
  switch (cat) {
    case "P1":
      return { bg: "bg-emerald-950/40", text: "text-emerald-400", border: "border-emerald-600/40", bar: "bg-emerald-500" };
    case "P2":
      return { bg: "bg-blue-950/40", text: "text-blue-400", border: "border-blue-600/40", bar: "bg-blue-500" };
    case "P3":
      return { bg: "bg-amber-950/40", text: "text-amber-400", border: "border-amber-600/40", bar: "bg-amber-500" };
    case "P4":
    default:
      return { bg: "bg-rose-950/40", text: "text-rose-400", border: "border-rose-600/40", bar: "bg-rose-500" };
  }
}

// Category titles derived from Approved_Flag labels in the training dataset.
// Neutral categorical tiers P1-P4 directly corresponding to dataset classes.
function getCategoryTitle(cat: string): string {
  switch (cat) {
    case "P1":
      return "Category P1";
    case "P2":
      return "Category P2";
    case "P3":
      return "Category P3";
    case "P4":
      return "Category P4";
    default:
      return `Category ${cat}`;
  }
}

export default function CreditRiskPage() {
  const [samples, setSamples] = useState<BorrowerProfileSample[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>("p2_sample");
  const [features, setFeatures] = useState<Record<string, string | number>>(DEFAULT_SAMPLE_FEATURES);
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false);

  const [scoreResult, setScoreResult] = useState<CreditScoreResponse | null>(null);
  const [explainResult, setExplainResult] = useState<CreditExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // What-if state
  const [whatIfMissed, setWhatIfMissed] = useState<number>(0);
  const [whatIfEnq, setWhatIfEnq] = useState<number>(0);
  const [whatIfIncome, setWhatIfIncome] = useState<number>(45000);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResponse | null>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);

  // Fetch samples on load
  useEffect(() => {
    async function loadSamples() {
      try {
        const data = await api.credit.samples();
        setSamples(data);
        if (data.length > 0) {
          const defaultSample = data.find((s) => s.sample_id === "p2_sample" || s.sample_id === "p2_standard") || data[0];
          setSelectedSampleId(defaultSample.sample_id);
          setFeatures(defaultSample.features);
          setWhatIfMissed(Number(defaultSample.features.Tot_Missed_Pmnt) || 0);
          setWhatIfEnq(Number(defaultSample.features.enq_L3m) || 0);
          setWhatIfIncome(Number(defaultSample.features.NETMONTHLYINCOME) || 45000);
        }
      } catch (err) {
        console.warn("Could not load sample borrower profiles:", err);
      }
    }
    loadSamples();
  }, []);

  function handleSelectSample(sampleId: string) {
    setSelectedSampleId(sampleId);
    const sample = samples.find((s) => s.sample_id === sampleId);
    if (sample) {
      setFeatures(sample.features);
      setWhatIfMissed(Number(sample.features.Tot_Missed_Pmnt) || 0);
      setWhatIfEnq(Number(sample.features.enq_L3m) || 0);
      setWhatIfIncome(Number(sample.features.NETMONTHLYINCOME) || 45000);
      setScoreResult(null);
      setExplainResult(null);
      setWhatIfResult(null);
    }
  }

  function handleFeatureChange(key: string, val: string | number) {
    setFeatures((prev) => ({ ...prev, [key]: val }));
  }

  async function handleScoreAndExplain() {
    setLoading(true);
    setError(null);
    setWhatIfResult(null);
    try {
      const [score, explain] = await Promise.all([
        api.credit.score(features),
        api.credit.explain(features, 8),
      ]);
      setScoreResult(score);
      setExplainResult(explain);
      setWhatIfMissed(Number(features.Tot_Missed_Pmnt) || 0);
      setWhatIfEnq(Number(features.enq_L3m) || 0);
      setWhatIfIncome(Number(features.NETMONTHLYINCOME) || 45000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error executing credit assessment.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRunWhatIf() {
    if (!scoreResult) return;
    setWhatIfLoading(true);
    try {
      const modifications: Record<string, number> = {
        Tot_Missed_Pmnt: Number(whatIfMissed),
        enq_L3m: Number(whatIfEnq),
        NETMONTHLYINCOME: Number(whatIfIncome),
      };
      const res = await api.credit.whatIf(features, modifications);
      setWhatIfResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "What-if simulation error.");
    } finally {
      setWhatIfLoading(false);
    }
  }

  const category = scoreResult?.predicted_category || "P2";
  const colors = getCategoryColor(category);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                <CreditCard className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                  Indian Credit Risk Intelligence
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono">
                    Multiclass P1–P4
                  </span>
                </h1>
                <p className="text-sm text-slate-400 mt-0.5">
                  Explainable four-tier credit risk classification benchmarked on 51,336 Indian banking & CIBIL records.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleScoreAndExplain}
              disabled={loading}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm flex items-center gap-2 transition-all shadow-lg shadow-indigo-600/20 cursor-pointer"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  Scoring & Explaining...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  Score & Explain Profile
                </>
              )}
            </button>
          </div>
        </div>

        {/* Academic / Regulatory Disclosure */}
        <div className="mt-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-start gap-3">
          <Info className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
          <div>
            <span className="font-semibold text-slate-300">Methodological Disclosure:</span> This assessment predicts relative credit tiers (<code className="text-indigo-300">P1</code>–<code className="text-rose-300">P4</code>) using an XGBoost multiclass model trained on a 70/15/15 stratified partition of Indian banking and bureau data (51,336 records). The P1–P4 labels are the original <code className="text-indigo-300">Approved_Flag</code> column values from the dataset — they represent relative risk within this dataset, not regulated CIBIL score bands or official Indian default categories. This tool does <strong className="text-slate-200">not</strong> estimate an official CIBIL score, compute a probability of default, or guarantee credit approval.
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Form & Demonstrations (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Sample Profile Selector */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold tracking-wider uppercase text-slate-400 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                Select Demonstration Profile
              </span>
              <span className="text-xs text-slate-500">Non-sensitive reference cases</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {samples.map((s) => {
                const isSelected = selectedSampleId === s.sample_id;
                const catColor = getCategoryColor(s.expected_category);
                return (
                  <button
                    key={s.sample_id}
                    onClick={() => handleSelectSample(s.sample_id)}
                    className={`p-3 rounded-xl text-left border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-indigo-600/10 border-indigo-500 text-white shadow-md shadow-indigo-500/10"
                        : "bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded ${catColor.bg} ${catColor.text}`}>
                        {s.expected_category}
                      </span>
                      {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />}
                    </div>
                    <p className="text-xs font-medium text-slate-200 mt-2 line-clamp-1">{s.label}</p>
                    <p className="text-[11px] text-slate-500 line-clamp-1">{s.description.split(",")[0]}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Grouped Profile Inputs */}
          <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-indigo-400" />
                Borrower Credit Attributes
              </h2>
              <span className="text-xs font-mono text-slate-500">42 Validated Features</span>
            </div>
            <p className="text-xs text-slate-400 -mt-3">
              The bureau Credit Score is deliberately not used as an input. A variant that included it scored a near-perfect ROC-AUC of 0.9999
              because the risk tiers are derived from that score (target leakage), so it was rejected. This model uses the 42 trade-line and
              delinquency features only (ROC-AUC 0.9275, Macro-F1 0.678). See the Model Card for details.
            </p>

            {/* Section 1: Repayment & Delinquency History */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                1. Repayment & Delinquency Behavior
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Total Missed Payments (All Time)</label>
                  <input
                    type="number"
                    min="0"
                    max="20"
                    value={features.Tot_Missed_Pmnt ?? 0}
                    onChange={(e) => handleFeatureChange("Tot_Missed_Pmnt", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Instances of 60+ Days Past Due (DPD)</label>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    value={features.num_times_60p_dpd ?? 0}
                    onChange={(e) => handleFeatureChange("num_times_60p_dpd", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Recent Level of Delinquency Code</label>
                  <input
                    type="number"
                    min="0"
                    max="5"
                    value={features.recent_level_of_deliq ?? 0}
                    onChange={(e) => handleFeatureChange("recent_level_of_deliq", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Months Since Most Recent Payment</label>
                  <input
                    type="number"
                    min="0"
                    max="60"
                    value={features.time_since_recent_payment ?? 1}
                    onChange={(e) => handleFeatureChange("time_since_recent_payment", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Section 2: Credit Accounts & Trade Lines */}
            <div className="space-y-3 pt-2 border-t border-slate-800/60">
              <h3 className="text-xs font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5" />
                2. Credit Accounts & Trade Lines
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Secured Trade Lines</label>
                  <input
                    type="number"
                    min="0"
                    value={features.Secured_TL ?? 0}
                    onChange={(e) => handleFeatureChange("Secured_TL", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Unsecured Trade Lines</label>
                  <input
                    type="number"
                    min="0"
                    value={features.Unsecured_TL ?? 1}
                    onChange={(e) => handleFeatureChange("Unsecured_TL", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Home Loan Accounts</label>
                  <input
                    type="number"
                    min="0"
                    value={features.Home_TL ?? 0}
                    onChange={(e) => handleFeatureChange("Home_TL", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Personal Loans (PL)</label>
                  <input
                    type="number"
                    min="0"
                    value={features.PL_TL ?? 1}
                    onChange={(e) => handleFeatureChange("PL_TL", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Age of Oldest Account (Mo)</label>
                  <input
                    type="number"
                    min="1"
                    value={features.Age_Oldest_TL ?? 48}
                    onChange={(e) => handleFeatureChange("Age_Oldest_TL", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Age of Newest Account (Mo)</label>
                  <input
                    type="number"
                    min="1"
                    value={features.Age_Newest_TL ?? 6}
                    onChange={(e) => handleFeatureChange("Age_Newest_TL", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Section 3: Inquiries & Bureau Activity */}
            <div className="space-y-3 pt-2 border-t border-slate-800/60">
              <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5" />
                3. Inquiries & Bureau Activity
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Enquiries in Last 3 Months</label>
                  <input
                    type="number"
                    min="0"
                    max="20"
                    value={features.enq_L3m ?? 0}
                    onChange={(e) => handleFeatureChange("enq_L3m", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">PL Enquiries in Last 12M</label>
                  <input
                    type="number"
                    min="0"
                    value={features.PL_enq_L12m ?? 0}
                    onChange={(e) => handleFeatureChange("PL_enq_L12m", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Months Since Recent Enquiry</label>
                  <input
                    type="number"
                    min="0"
                    value={features.time_since_recent_enq ?? 6}
                    onChange={(e) => handleFeatureChange("time_since_recent_enq", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>

            {/* Section 4: Borrower Profile & Employment */}
            <div className="space-y-3 pt-2 border-t border-slate-800/60">
              <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5" />
                4. Borrower Profile & Employment
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Net Monthly Income (INR)</label>
                  <input
                    type="number"
                    min="5000"
                    step="1000"
                    value={features.NETMONTHLYINCOME ?? 45000}
                    onChange={(e) => handleFeatureChange("NETMONTHLYINCOME", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Employer Tenure (Months)</label>
                  <input
                    type="number"
                    min="1"
                    value={features.Time_With_Curr_Empr ?? 36}
                    onChange={(e) => handleFeatureChange("Time_With_Curr_Empr", Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Marital Status</label>
                  <select
                    value={features.MARITALSTATUS ?? "Married"}
                    onChange={(e) => handleFeatureChange("MARITALSTATUS", e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="Married">Married</option>
                    <option value="Single">Single</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Education Level</label>
                  <select
                    value={features.EDUCATION ?? "GRADUATE"}
                    onChange={(e) => handleFeatureChange("EDUCATION", e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="GRADUATE">Graduate</option>
                    <option value="POST-GRADUATE">Post-Graduate</option>
                    <option value="UNDER GRADUATE">Undergraduate</option>
                    <option value="12TH">12th Standard</option>
                    <option value="SSC">SSC (10th)</option>
                    <option value="PROFESSIONAL">Professional</option>
                    <option value="OTHERS">Others</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Borrower Gender</label>
                  <select
                    value={features.GENDER ?? "M"}
                    onChange={(e) => handleFeatureChange("GENDER", e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="M">Male (M)</option>
                    <option value="F">Female (F)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Section 5: Advanced Trade Line & Delinquency Attributes (Remaining 25 Features) */}
            <div className="pt-2 border-t border-slate-800/60">
              <button
                type="button"
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="w-full flex items-center justify-between py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 transition cursor-pointer"
              >
                <span className="flex items-center gap-1.5 uppercase tracking-wider text-indigo-400">
                  <Sliders className="w-3.5 h-3.5" />
                  5. Detailed Trade-Line &amp; Inquiry Attributes ({showAdvanced ? "Expanded" : "25 Additional Features"})
                </span>
                {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>

              {showAdvanced ? (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-3 animate-fade-in text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Ratio Open TLs (L6M)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={features.pct_tl_open_L6M ?? 0}
                      onChange={(e) => handleFeatureChange("pct_tl_open_L6M", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Ratio Closed TLs (L6M)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={features.pct_tl_closed_L6M ?? 0}
                      onChange={(e) => handleFeatureChange("pct_tl_closed_L6M", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Closed TLs in L12M</label>
                    <input
                      type="number"
                      min="0"
                      value={features.Tot_TL_closed_L12M ?? 0}
                      onChange={(e) => handleFeatureChange("Tot_TL_closed_L12M", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Ratio Closed TLs (L12M)</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={features.pct_tl_closed_L12M ?? 0}
                      onChange={(e) => handleFeatureChange("pct_tl_closed_L12M", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Credit Card Accounts (CC_TL)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.CC_TL ?? 1}
                      onChange={(e) => handleFeatureChange("CC_TL", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Other Accounts (Other_TL)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.Other_TL ?? 0}
                      onChange={(e) => handleFeatureChange("Other_TL", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Max Recent Delinq Level</label>
                    <input
                      type="number"
                      min="0"
                      max="5"
                      value={features.max_recent_level_of_deliq ?? 0}
                      onChange={(e) => handleFeatureChange("max_recent_level_of_deliq", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Delinquency Count (6-12M)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.num_deliq_6_12mts ?? 0}
                      onChange={(e) => handleFeatureChange("num_deliq_6_12mts", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Standard Months (12M)</label>
                    <input
                      type="number"
                      min="0"
                      max="12"
                      value={features.num_std_12mts ?? 12}
                      onChange={(e) => handleFeatureChange("num_std_12mts", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Substandard Accounts</label>
                    <input
                      type="number"
                      min="0"
                      value={features.num_sub ?? 0}
                      onChange={(e) => handleFeatureChange("num_sub", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Substandard (6M)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.num_sub_6mts ?? 0}
                      onChange={(e) => handleFeatureChange("num_sub_6mts", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Substandard (12M)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.num_sub_12mts ?? 0}
                      onChange={(e) => handleFeatureChange("num_sub_12mts", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Doubtful Accounts (num_dbt)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.num_dbt ?? 0}
                      onChange={(e) => handleFeatureChange("num_dbt", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Doubtful Accounts (12M)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.num_dbt_12mts ?? 0}
                      onChange={(e) => handleFeatureChange("num_dbt_12mts", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Loss Accounts (num_lss)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.num_lss ?? 0}
                      onChange={(e) => handleFeatureChange("num_lss", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">CC Enquiries (12M)</label>
                    <input
                      type="number"
                      min="0"
                      value={features.CC_enq_L12m ?? 0}
                      onChange={(e) => handleFeatureChange("CC_enq_L12m", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Credit Card Flag (0/1)</label>
                    <select
                      value={features.CC_Flag ?? 1}
                      onChange={(e) => handleFeatureChange("CC_Flag", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    >
                      <option value={1}>1 (Active Card)</option>
                      <option value={0}>0 (No Card)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Personal Loan Flag (0/1)</label>
                    <select
                      value={features.PL_Flag ?? 0}
                      onChange={(e) => handleFeatureChange("PL_Flag", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    >
                      <option value={1}>1 (Active PL)</option>
                      <option value={0}>0 (No PL)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Home Loan Flag (0/1)</label>
                    <select
                      value={features.HL_Flag ?? 0}
                      onChange={(e) => handleFeatureChange("HL_Flag", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    >
                      <option value={1}>1 (Active HL)</option>
                      <option value={0}>0 (No HL)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Gold Loan Flag (0/1)</label>
                    <select
                      value={features.GL_Flag ?? 0}
                      onChange={(e) => handleFeatureChange("GL_Flag", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    >
                      <option value={1}>1 (Active GL)</option>
                      <option value={0}>0 (No GL)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Ratio PL Enq L6M of Ever</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={features.pct_PL_enq_L6m_of_ever ?? 0}
                      onChange={(e) => handleFeatureChange("pct_PL_enq_L6m_of_ever", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Ratio CC Enq L6M of Ever</label>
                    <input
                      type="number"
                      step="0.05"
                      min="0"
                      max="1"
                      value={features.pct_CC_enq_L6m_of_ever ?? 0}
                      onChange={(e) => handleFeatureChange("pct_CC_enq_L6m_of_ever", Number(e.target.value))}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Last Enquired Product</label>
                    <select
                      value={features.last_prod_enq2 ?? "PL"}
                      onChange={(e) => handleFeatureChange("last_prod_enq2", e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="PL">PL (Personal Loan)</option>
                      <option value="CC">CC (Credit Card)</option>
                      <option value="HL">HL (Home Loan)</option>
                      <option value="AL">AL (Auto Loan)</option>
                      <option value="ConsumerLoan">Consumer Loan</option>
                      <option value="others">Others</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">First Enquired Product</label>
                    <select
                      value={features.first_prod_enq2 ?? "CC"}
                      onChange={(e) => handleFeatureChange("first_prod_enq2", e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="CC">CC (Credit Card)</option>
                      <option value="PL">PL (Personal Loan)</option>
                      <option value="HL">HL (Home Loan)</option>
                      <option value="AL">AL (Auto Loan)</option>
                      <option value="ConsumerLoan">Consumer Loan</option>
                      <option value="others">Others</option>
                    </select>
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-slate-500 pt-1">
                  ✓ All 42 candidate features mapped and active (click to expand / customize trade lines and inquiry ratios).
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Prediction Results, SHAP, and What-If (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Prediction Result Card */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {scoreResult ? (
            <div className={`p-6 rounded-2xl border ${colors.border} ${colors.bg} space-y-5 animate-fade-in`}>
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Predicted Credit Category</span>
                  <div className="flex items-baseline gap-3 mt-1">
                    <span className={`text-4xl font-extrabold font-mono ${colors.text}`}>
                      {scoreResult.predicted_category}
                    </span>
                    <span className="text-sm font-medium text-slate-300">
                      {getCategoryTitle(scoreResult.predicted_category)}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-400 block">Model Version</span>
                  <span className="text-xs font-mono text-indigo-300">{scoreResult.model_version}</span>
                </div>
              </div>

              {/* Class Probability Breakdown */}
              {scoreResult.class_probabilities && (
                <div className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
                    Model Class Probabilities (P1–P4 Category Likelihoods)
                  </span>
                  <p className="text-[10px] text-slate-500">
                    These are genuine multiclass model output probabilities for each dataset category (P1–P4). They are not calibrated probabilities of default.
                  </p>
                  <div className="space-y-1.5">
                    {Object.entries(scoreResult.class_probabilities).map(([cls, prob]) => {
                      const cColor = getCategoryColor(cls);
                      const pct = Math.round(prob * 100);
                      const isWinner = cls === scoreResult.predicted_category;
                      return (
                        <div key={cls} className="space-y-0.5">
                          <div className="flex justify-between text-xs">
                            <span className={`font-mono font-bold ${isWinner ? cColor.text : "text-slate-400"}`}>
                              {cls} {isWinner ? "★ (Predicted)" : ""}
                            </span>
                            <span className="font-mono text-slate-300">{pct}% ({prob.toFixed(4)})</span>
                          </div>
                          <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${cColor.bar} transition-all duration-500`}
                              style={{ width: `${Math.max(pct, 2)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Warnings */}
              {scoreResult.warnings && scoreResult.warnings.length > 0 && (
                <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/40 text-xs text-amber-300 space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Input Validation Notice
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300">
                    {scoreResult.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Disclaimer */}
              <p className="text-[11px] text-slate-500 leading-relaxed border-t border-slate-800 pt-3">
                {scoreResult.proxy_dataset_disclaimer ||
                  "Predictions are relative classifications within historical benchmarks and do not guarantee credit approval."}
              </p>
            </div>
          ) : (
            <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800 text-center text-slate-500 space-y-3">
              <CreditCard className="w-10 h-10 mx-auto text-slate-600 stroke-[1.5]" />
              <p className="text-sm font-medium text-slate-400">No Assessment Run Yet</p>
              <p className="text-xs text-slate-500 max-w-xs mx-auto">
                Select a reference profile or adjust features on the left, then click <strong>Score & Explain Profile</strong>.
              </p>
            </div>
          )}

          {/* Explainability (SHAP) Card */}
          {explainResult && explainResult.top_contributions && explainResult.top_contributions.length > 0 && (
            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  SHAP Explainability Waterfall
                </h3>
                <span className="text-xs font-mono text-slate-500">Tier {explainResult.predicted_category} Impact</span>
              </div>
              <div className="space-y-2.5">
                {explainResult.top_contributions.map((c, idx) => {
                  const isReducesRisk = c.impact_direction === "REDUCES_RISK";
                  const friendlyName =
                    FEATURE_DESCRIPTIONS[c.feature_name.split("__").pop() || c.feature_name] ||
                    c.feature_name.split("__").pop();
                  return (
                    <div
                      key={idx}
                      className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between text-xs"
                    >
                      <div className="space-y-0.5">
                        <span className="font-medium text-slate-200 block">{friendlyName}</span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          Value: {String(c.feature_value)}
                        </span>
                      </div>
                      <div className="text-right flex items-center gap-2">
                        <div className="space-y-0.5">
                          <span
                            className={`font-mono font-semibold block ${
                              isReducesRisk ? "text-emerald-400" : "text-rose-400"
                            }`}
                          >
                            {c.shap_value > 0 ? `+${c.shap_value.toFixed(4)}` : c.shap_value.toFixed(4)}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            {isReducesRisk ? "Favorable" : "Stress Driver"}
                          </span>
                        </div>
                        {isReducesRisk ? (
                          <TrendingDown className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <TrendingUp className="w-4 h-4 text-rose-400 shrink-0" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* What-If Counterfactual Lab */}
          {scoreResult && (
            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-indigo-400" />
                  What-If Counterfactual Lab
                </h3>
                <span className="text-xs text-slate-500">Hypothetical Simulation</span>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Modified Missed Payments</span>
                    <span className="font-mono text-indigo-300">{whatIfMissed}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    value={whatIfMissed}
                    onChange={(e) => setWhatIfMissed(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Modified Enquiries (Last 3M)</span>
                    <span className="font-mono text-indigo-300">{whatIfEnq}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="12"
                    value={whatIfEnq}
                    onChange={(e) => setWhatIfEnq(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Modified Monthly Income</span>
                    <span className="font-mono text-indigo-300">₹{whatIfIncome.toLocaleString()}</span>
                  </div>
                  <input
                    type="range"
                    min="10000"
                    max="150000"
                    step="5000"
                    value={whatIfIncome}
                    onChange={(e) => setWhatIfIncome(Number(e.target.value))}
                    className="w-full accent-indigo-500"
                  />
                </div>

                <button
                  onClick={handleRunWhatIf}
                  disabled={whatIfLoading}
                  className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs transition-colors cursor-pointer flex items-center justify-center gap-2"
                >
                  {whatIfLoading ? "Simulating Counterfactual..." : "Simulate Scenario Shift"}
                </button>
              </div>

              {/* What-If Results */}
              {whatIfResult && (
                <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-3 animate-fade-in text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-[11px] text-slate-500 block">Baseline Tier</span>
                      <span className="font-mono font-bold text-slate-200">
                        {whatIfResult.baseline_category || scoreResult.predicted_category}
                      </span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-600" />
                    <div className="text-right">
                      <span className="text-[11px] text-slate-500 block">Simulated Tier</span>
                      <span
                        className={`font-mono font-bold ${
                          getCategoryColor(whatIfResult.counterfactual_category || "P2").text
                        }`}
                      >
                        {whatIfResult.counterfactual_category || "P2"}
                      </span>
                    </div>
                  </div>

                  <div className="border-t border-slate-800 pt-2 flex items-center justify-between">
                    <span className="text-slate-400">Shift Direction:</span>
                    <span
                      className={`font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${
                        whatIfResult.direction_of_change.includes("UPGRADED") || whatIfResult.direction_of_change.includes("REDUCED")
                          ? "bg-emerald-950/40 text-emerald-400 border border-emerald-800/40"
                          : whatIfResult.direction_of_change === "UNCHANGED"
                          ? "bg-slate-800 text-slate-400"
                          : "bg-rose-950/40 text-rose-400 border border-rose-800/40"
                      }`}
                    >
                      {whatIfResult.direction_of_change}
                    </span>
                  </div>

                  <p className="text-[10px] text-slate-500 pt-1">
                    *Counterfactual simulations test model sensitivity under hypothetical input variations.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
