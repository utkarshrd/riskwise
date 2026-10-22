"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Sliders } from "lucide-react";
import { Alert, Card, CardHeader, Field as FormField, inputClass } from "@/components/ui";
import { ADVANCED_FIELDS, FIELD_GROUPS, type Field, type FeatureValues } from "../_lib/fields";

function FeatureInput({
  field,
  values,
  onChange,
  compact = false,
}: {
  field: Field;
  values: FeatureValues;
  onChange: (key: string, value: string | number) => void;
  compact?: boolean;
}) {
  const id = `credit-${field.key}`;
  const value = values[field.key] ?? field.fallback;
  const sizing = compact ? "py-1.5" : "";

  return (
    <FormField label={field.label} htmlFor={id}>
      {field.kind === "number" ? (
        <input
          id={id}
          type="number"
          min={field.min}
          max={field.max}
          step={field.step}
          value={value}
          onChange={(e) => onChange(field.key, Number(e.target.value))}
          className={`${inputClass} ${sizing}`}
        />
      ) : (
        <select
          id={id}
          value={value}
          onChange={(e) => {
            // flag fields hold numbers, text fields hold strings; keep each in its original type
            const isNumeric = typeof field.fallback === "number";
            onChange(field.key, isNumeric ? Number(e.target.value) : e.target.value);
          }}
          className={`${inputClass} ${sizing}`}
        >
          {field.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
    </FormField>
  );
}

interface FeatureFormProps {
  values: FeatureValues;
  onChange: (key: string, value: string | number) => void;
}

export default function FeatureForm({ values, onChange }: FeatureFormProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const featureCount = FIELD_GROUPS.reduce((n, g) => n + g.fields.length, 0) + ADVANCED_FIELDS.length;

  return (
    <Card className="space-y-6">
      <CardHeader
        className="border-b border-slate-200 dark:border-slate-800 pb-4"
        icon={<Sliders className="w-4 h-4 text-indigo-500" />}
        title="Borrower Credit Attributes"
        right={<span className="font-mono">{featureCount} model features</span>}
      />

      <Alert tone="info" title="The bureau Credit Score is not an input">
        A variant that included it scored a near-perfect ROC-AUC of 0.9999, because the risk tiers are derived from that score (target leakage), so it was rejected. The model used here relies on the {featureCount} trade-line, delinquency and profile features only (ROC-AUC 0.9275, Macro-F1 0.678). See the Model Card for details.
      </Alert>

      {FIELD_GROUPS.map((group, i) => {
        const Icon = group.icon;
        return (
          <section key={group.title} className={`space-y-3 ${i > 0 ? "pt-2 border-t border-slate-200/70 dark:border-slate-800/60" : ""}`}>
            <h3 className={`text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 ${group.accent}`}>
              <Icon className="w-3.5 h-3.5" />
              {group.title}
            </h3>
            <div className={`grid grid-cols-1 ${group.columns} gap-4`}>
              {group.fields.map((f) => (
                <FeatureInput key={f.key} field={f} values={values} onChange={onChange} />
              ))}
            </div>
          </section>
        );
      })}

      <section className="pt-2 border-t border-slate-200/70 dark:border-slate-800/60">
        <button
          type="button"
          onClick={() => setShowAdvanced((v) => !v)}
          aria-expanded={showAdvanced}
          className="w-full flex items-center justify-between py-2 text-xs font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition"
        >
          <span className="flex items-center gap-1.5 uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
            <Sliders className="w-3.5 h-3.5" />
            5. Detailed Trade-Line &amp; Inquiry Attributes ({ADVANCED_FIELDS.length} more features)
          </span>
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showAdvanced ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-3 animate-fade-in">
            {ADVANCED_FIELDS.map((f) => (
              <FeatureInput key={f.key} field={f} values={values} onChange={onChange} compact />
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-slate-500 pt-1">
            All {featureCount} features are active with the values shown. Expand to edit the detailed trade-line and enquiry fields.
          </p>
        )}
      </section>
    </Card>
  );
}
