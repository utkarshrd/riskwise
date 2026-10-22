"use client";

import { Alert } from "@/components/ui";
import CreditHeader from "./_components/CreditHeader";
import FeatureForm from "./_components/FeatureForm";
import PredictionCard from "./_components/PredictionCard";
import SampleSelector from "./_components/SampleSelector";
import ShapCard from "./_components/ShapCard";
import WhatIfLab from "./_components/WhatIfLab";
import { useCreditAssessment } from "./_hooks/useCreditAssessment";

export default function CreditRiskPage() {
  const a = useCreditAssessment();

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      <CreditHeader loading={a.loading} onScore={a.scoreAndExplain} />

      {a.error && (
        <Alert
          tone="error"
          title="Assessment failed"
          action={
            <button type="button" onClick={a.scoreAndExplain} className="text-[11px] font-semibold underline shrink-0">
              Retry
            </button>
          }
        >
          {a.error}
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-7 space-y-6 min-w-0">
          <SampleSelector
            samples={a.samples}
            loading={a.samplesLoading}
            error={a.samplesError}
            selectedId={a.selectedSampleId}
            onSelect={a.selectSample}
          />
          <FeatureForm values={a.features} onChange={a.setFeature} />
        </div>

        <div className="lg:col-span-5 space-y-6 min-w-0">
          <PredictionCard score={a.score} loading={a.loading} />
          {!a.loading && <ShapCard explain={a.explain} />}
          {!a.loading && <WhatIfLab score={a.score} whatIf={a.whatIf} />}
        </div>
      </div>
    </div>
  );
}
