import { Activity, HelpCircle, ShieldCheck } from "lucide-react";
import type { VaRValidationResponse } from "@/lib/api";
import { Badge, Card, CardHeader, MetricInfo } from "@/components/ui";
import { formatNumber } from "@/lib/format";

function Reading({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-slate-400">{label}</div>
      <div className="font-bold text-slate-800 dark:text-slate-200">{value}</div>
    </div>
  );
}

const readingsBox =
  "grid grid-cols-2 gap-2 p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs font-mono";

export default function CoverageTests({ result: r }: { result: VaRValidationResponse }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card className="space-y-3">
        <CardHeader
          icon={<ShieldCheck className="w-4 h-4 text-indigo-500" />}
          title={
            <span className="inline-flex items-center gap-1">
              Kupiec POF Test <MetricInfo metric="kupiec" />
            </span>
          }
          right={
            <Badge tone={r.kupiec_test_passed ? "green" : "red"} className="font-bold">
              {r.kupiec_test_passed ? "PASSED" : "REJECTED"}
            </Badge>
          }
        />
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          Unconditional coverage: do exceptions occur at the expected rate (H0: true exception probability p = {r.expected_exception_rate})?
          {r.kupiec_test_passed ? " The model is not rejected." : " The model is miscalibrated."}
        </p>
        <div className={readingsBox}>
          <Reading label="Likelihood ratio (LR)" value={formatNumber(r.kupiec_lr_stat, 4)} />
          <Reading label="p-value (df=1)" value={formatNumber(r.kupiec_p_value, 4)} />
        </div>
        <div className="text-[11px] text-slate-400 flex items-start gap-1.5 pt-1">
          <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>Critical value at α=0.05 is χ²(1)=3.841. Passing does not prove the model is right: with few observations the test has little power.</span>
        </div>
      </Card>

      <Card className="space-y-3">
        <CardHeader
          icon={<Activity className="w-4 h-4 text-emerald-500" />}
          title={
            <span className="inline-flex items-center gap-1">
              Christoffersen Tests <MetricInfo metric="christoffersen" />
            </span>
          }
          right={
            r.christoffersen_test_passed == null ? (
              <Badge className="font-bold">NOT AVAILABLE</Badge>
            ) : (
              <Badge tone={r.christoffersen_test_passed ? "green" : "red"} className="font-bold">
                {r.christoffersen_test_passed ? "INDEPENDENT" : "CLUSTERING"}
              </Badge>
            )
          }
        />
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          Independence: are exceptions spread out, or do they bunch together in turbulent periods? Combined with Kupiec this gives conditional coverage.
        </p>
        <div className={readingsBox}>
          <Reading label="Independence LR" value={formatNumber(r.christoffersen_lr_stat, 4)} />
          <Reading label="p-value (df=1)" value={formatNumber(r.christoffersen_p_value, 4)} />
          <Reading label="Conditional coverage LR (df=2)" value={formatNumber(r.christoffersen_cc_stat, 4)} />
          <Reading label="Conditional coverage p-value" value={formatNumber(r.christoffersen_cc_p_value, 4)} />
        </div>

        {r.basel_capital_multiplier != null && (
          <div className="flex items-center justify-between p-2.5 rounded-lg bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-xs font-mono">
            <span className="text-amber-800 dark:text-amber-300 font-semibold">Basel capital multiplier</span>
            <span className="font-bold text-amber-700 dark:text-amber-200 text-base">{r.basel_capital_multiplier.toFixed(2)}×</span>
          </div>
        )}

        <div className="text-[11px] text-slate-400 flex items-start gap-1.5 pt-1">
          <HelpCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>Conditional coverage: LR_cc = LR_pof + LR_ind, distributed χ²(2) under the null.</span>
        </div>
      </Card>
    </div>
  );
}
