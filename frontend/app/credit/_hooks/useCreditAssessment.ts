"use client";

import { useEffect, useState } from "react";
import {
  api,
  type BorrowerProfileSample,
  type CreditExplainResponse,
  type CreditScoreResponse,
  type WhatIfResponse,
} from "@/lib/api";
import { DEFAULT_FEATURES, type FeatureValues } from "../_lib/fields";

const DEFAULT_INCOME = 45000;

/** Reference profiles, the editable feature set, scoring with SHAP, and the what-if simulation. */
export function useCreditAssessment() {
  const [samples, setSamples] = useState<BorrowerProfileSample[]>([]);
  const [samplesLoading, setSamplesLoading] = useState(true);
  const [samplesError, setSamplesError] = useState<string | null>(null);
  const [selectedSampleId, setSelectedSampleId] = useState("p2_sample");
  const [features, setFeatures] = useState<FeatureValues>(DEFAULT_FEATURES);

  const [score, setScore] = useState<CreditScoreResponse | null>(null);
  const [explain, setExplain] = useState<CreditExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [whatIfMissed, setWhatIfMissed] = useState(0);
  const [whatIfEnquiries, setWhatIfEnquiries] = useState(0);
  const [whatIfIncome, setWhatIfIncome] = useState(DEFAULT_INCOME);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResponse | null>(null);
  const [whatIfLoading, setWhatIfLoading] = useState(false);

  const syncWhatIf = (f: FeatureValues) => {
    setWhatIfMissed(Number(f.Tot_Missed_Pmnt) || 0);
    setWhatIfEnquiries(Number(f.enq_L3m) || 0);
    setWhatIfIncome(Number(f.NETMONTHLYINCOME) || DEFAULT_INCOME);
  };

  useEffect(() => {
    let cancelled = false;
    api.credit
      .samples()
      .then((data) => {
        if (cancelled) return;
        setSamples(data);
        const initial = data.find((s) => s.sample_id === "p2_sample" || s.sample_id === "p2_standard") || data[0];
        if (initial) {
          setSelectedSampleId(initial.sample_id);
          setFeatures(initial.features);
          setWhatIfMissed(Number(initial.features.Tot_Missed_Pmnt) || 0);
          setWhatIfEnquiries(Number(initial.features.enq_L3m) || 0);
          setWhatIfIncome(Number(initial.features.NETMONTHLYINCOME) || DEFAULT_INCOME);
        }
      })
      .catch((err) => !cancelled && setSamplesError(err instanceof Error ? err.message : "Could not load reference profiles."))
      .finally(() => !cancelled && setSamplesLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const selectSample = (sampleId: string) => {
    const sample = samples.find((s) => s.sample_id === sampleId);
    if (!sample) return;
    setSelectedSampleId(sampleId);
    setFeatures(sample.features);
    syncWhatIf(sample.features);
    setScore(null);
    setExplain(null);
    setWhatIfResult(null);
    setError(null);
  };

  const setFeature = (key: string, value: string | number) => setFeatures((prev) => ({ ...prev, [key]: value }));

  const scoreAndExplain = async () => {
    setLoading(true);
    setError(null);
    setWhatIfResult(null);
    try {
      const [s, e] = await Promise.all([api.credit.score(features), api.credit.explain(features, 8)]);
      setScore(s);
      setExplain(e);
      syncWhatIf(features);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The credit assessment failed.");
    } finally {
      setLoading(false);
    }
  };

  const runWhatIf = async () => {
    if (!score) return;
    setWhatIfLoading(true);
    try {
      setWhatIfResult(
        await api.credit.whatIf(features, {
          Tot_Missed_Pmnt: whatIfMissed,
          enq_L3m: whatIfEnquiries,
          NETMONTHLYINCOME: whatIfIncome,
        })
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "The what-if simulation failed.");
    } finally {
      setWhatIfLoading(false);
    }
  };

  return {
    samples,
    samplesLoading,
    samplesError,
    selectedSampleId,
    features,
    score,
    explain,
    loading,
    error,
    whatIf: {
      missed: whatIfMissed,
      enquiries: whatIfEnquiries,
      income: whatIfIncome,
      result: whatIfResult,
      loading: whatIfLoading,
      setMissed: setWhatIfMissed,
      setEnquiries: setWhatIfEnquiries,
      setIncome: setWhatIfIncome,
      run: runWhatIf,
    },
    selectSample,
    setFeature,
    scoreAndExplain,
  };
}
