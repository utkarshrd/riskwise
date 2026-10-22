"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface WaterfallItem {
  label: string;
  /** Contribution as a fraction of the portfolio, e.g. -0.05 for a 5% loss. */
  value: number;
}

interface WaterfallChartProps {
  items: WaterfallItem[];
  totalLabel?: string;
  height?: number;
}

interface Step {
  label: string;
  range: [number, number];
  value: number;
  total: boolean;
}

const LOSS = "#e11d48";
const GAIN = "#059669";
const TOTAL = "#4f46e5";

/** Each bar floats from the running total before it to the running total after it; the last bar is the sum. */
export default function WaterfallChart({ items, totalLabel = "Portfolio", height = 288 }: WaterfallChartProps) {
  const steps = useMemo<Step[]>(() => {
    const out: Step[] = [];
    let running = 0;
    for (const item of items) {
      const from = running;
      const next = from + item.value * 100;
      out.push({
        label: item.label,
        range: [Math.min(from, next), Math.max(from, next)],
        value: item.value * 100,
        total: false,
      });
      running = next;
    }
    out.push({ label: totalLabel, range: [Math.min(0, running), Math.max(0, running)], value: running, total: true });
    return out;
  }, [items, totalLabel]);

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={steps} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.3} vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} stroke="#94a3b8" interval={0} />
          <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" tickFormatter={(v) => `${Number(v).toFixed(0)}%`} />
          <ReferenceLine y={0} stroke="#94a3b8" />
          <Tooltip
            cursor={{ fill: "rgba(148,163,184,0.12)" }}
            contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.5rem", color: "#f8fafc", fontSize: "11px" }}
            formatter={(_v, _n, entry) => {
              const step = (entry as { payload?: Step }).payload;
              return [step ? `${step.value >= 0 ? "+" : ""}${step.value.toFixed(2)}%` : "", step?.total ? "Total" : "Contribution"];
            }}
          />
          <Bar dataKey="range" radius={[2, 2, 2, 2]} isAnimationActive={false}>
            {steps.map((s) => (
              <Cell key={s.label} fill={s.total ? TOTAL : s.value < 0 ? LOSS : GAIN} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
