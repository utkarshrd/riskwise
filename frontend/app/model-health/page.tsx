"use client";

import { useEffect, useState } from "react";
import { Activity, Server } from "lucide-react";
import { Alert, Badge, Card, CardHeader, EmptyState, Skeleton, type Tone } from "@/components/ui";
import { api, type DriftRunResponse, type ModelRegistryItem } from "@/lib/api";

const DRIFT_TONE: Record<string, Tone> = { STABLE: "green", MODERATE: "amber", SIGNIFICANT: "red" };

function metric(m: ModelRegistryItem["metrics"], key: string, digits = 4): string {
  const v = m[key];
  return typeof v === "number" ? v.toFixed(digits) : "N/A";
}

export default function ModelHealthPage() {
  const [models, setModels] = useState<ModelRegistryItem[] | null>(null);
  const [modelsError, setModelsError] = useState<string | null>(null);

  const [drift, setDrift] = useState<DriftRunResponse | null>(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [driftError, setDriftError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.monitoring
      .models()
      .then((m) => !cancelled && setModels(m))
      .catch((err) => !cancelled && setModelsError(err instanceof Error ? err.message : "Could not load the model registry."));
    return () => {
      cancelled = true;
    };
  }, []);

  const runDrift = async () => {
    setDriftLoading(true);
    setDriftError(null);
    try {
      setDrift(await api.monitoring.runDrift());
    } catch (err) {
      setDrift(null);
      setDriftError(err instanceof Error ? err.message : "The drift check failed.");
    } finally {
      setDriftLoading(false);
    }
  };

  const worstFeatures = drift ? [...drift.features].sort((a, b) => b.psi_value - a.psi_value).slice(0, 10) : [];

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      <div>
        <Badge className="mb-2">Model registry</Badge>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">Model Registry & Drift Monitoring</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Registered model versions with their evaluation metrics, and Population Stability Index (PSI) checks on the input features.
        </p>
      </div>

      <Card className="space-y-4">
        <CardHeader icon={<Server className="w-4 h-4 text-indigo-500" />} title="Registered models" />

        {!models && !modelsError && <Skeleton className="h-24" />}
        {modelsError && <Alert tone="error">{modelsError}</Alert>}
        {models && models.length === 0 && (
          <EmptyState icon={<Server className="w-8 h-8" />} title="No models registered" description="Train a model to add it to the registry." />
        )}

        {models && models.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-500 uppercase text-[10px] tracking-wider border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="py-2 pr-3">Version</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3 text-right">ROC-AUC</th>
                  <th className="py-2 pr-3 text-right">Macro-F1</th>
                  <th className="py-2 pr-3 text-right">Accuracy</th>
                  <th className="py-2 pr-3 text-right">Log loss</th>
                  <th className="py-2">Trained</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                {models.map((m) => (
                  <tr key={m.id}>
                    <td className="py-2.5 pr-3">
                      <div className="font-semibold text-slate-900 dark:text-slate-100">{m.version}</div>
                      <div className="text-[10px] text-slate-400 font-sans">
                        {m.model_name} on {m.dataset_id} • sha256 {m.checksum.slice(0, 10)}…
                      </div>
                    </td>
                    <td className="py-2.5 pr-3">
                      <Badge tone={m.status === "active" ? "green" : "neutral"}>{m.status}</Badge>
                    </td>
                    <td className="py-2.5 pr-3 text-right">{metric(m.metrics, "roc_auc")}</td>
                    <td className="py-2.5 pr-3 text-right">{metric(m.metrics, "macro_f1")}</td>
                    <td className="py-2.5 pr-3 text-right">{metric(m.metrics, "accuracy")}</td>
                    <td className="py-2.5 pr-3 text-right">{metric(m.metrics, "log_loss")}</td>
                    <td className="py-2.5 text-slate-500 font-sans">{m.trained_at.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="space-y-4">
        <CardHeader
          icon={<Activity className="w-4 h-4 text-amber-500" />}
          title="Feature drift (PSI)"
          right={
            <button
              type="button"
              onClick={runDrift}
              disabled={driftLoading}
              className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold disabled:opacity-50"
            >
              {driftLoading ? "Running…" : "Run drift check"}
            </button>
          }
        />
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          PSI below 0.1 is stable, 0.1 to 0.25 is moderate and above 0.25 is significant. There is no live traffic yet, so this check compares two
          partitions of the training data. It validates the monitoring pipeline; it is not evidence about production drift.
        </p>

        {driftError && <Alert tone="error">{driftError}</Alert>}
        {driftLoading && <Skeleton className="h-40" />}

        {drift && !driftLoading && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="text-slate-500">Overall PSI</span>
              <span className="font-mono font-bold text-slate-900 dark:text-slate-100">{drift.overall_psi.toFixed(4)}</span>
              <Badge tone={DRIFT_TONE[drift.overall_status] ?? "neutral"}>{drift.overall_status}</Badge>
              <span className="text-slate-400">{drift.features.length} features checked</span>
            </div>
            {drift.drift_source && <Alert tone="info">Data used: {drift.drift_source}.</Alert>}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-slate-500 uppercase text-[10px] tracking-wider border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="py-2 pr-3">Feature (10 highest PSI)</th>
                    <th className="py-2 pr-3 text-right">PSI</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                  {worstFeatures.map((f) => (
                    <tr key={f.feature_name}>
                      <td className="py-2 pr-3 text-slate-800 dark:text-slate-200">{f.feature_name}</td>
                      <td className="py-2 pr-3 text-right">{f.psi_value.toFixed(4)}</td>
                      <td className="py-2">
                        <Badge tone={DRIFT_TONE[f.drift_status] ?? "neutral"}>{f.drift_status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
