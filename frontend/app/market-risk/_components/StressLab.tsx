"use client";

import { useMemo, useState } from "react";
import { Flame } from "lucide-react";
import { Card, CardHeader, Tabs } from "@/components/ui";
import type { StressInput } from "@/lib/api";
import { useStressLab } from "../_hooks/useStressLab";
import NamedEvents from "./NamedEvents";
import ReverseStress from "./ReverseStress";

interface StressLabProps {
  input: StressInput | null;
}

type Tab = "events" | "reverse";

export default function StressLab({ input }: StressLabProps) {
  const [tab, setTab] = useState<Tab>("events");
  // Re-key on the portfolio so a different run starts from a clean lab
  const key = useMemo(() => JSON.stringify(input), [input]);
  return <StressLabBody key={key} input={input} tab={tab} onTab={setTab} />;
}

function StressLabBody({ input, tab, onTab }: { input: StressInput | null; tab: Tab; onTab: (t: Tab) => void }) {
  const lab = useStressLab(input);
  if (!input) return null;

  return (
    <Card className="space-y-4">
      <CardHeader
        className="border-b border-slate-100 dark:border-slate-800 pb-3"
        icon={<Flame className="w-4 h-4 text-orange-500" />}
        title="Stress Lab"
        right="Real events and what-would-it-take"
      />
      <Tabs
        ariaLabel="Stress lab view"
        value={tab}
        onChange={onTab}
        tabs={[
          { id: "events", label: "Named market events" },
          { id: "reverse", label: "Reverse stress" },
        ]}
      />
      {tab === "events" ? (
        <NamedEvents replays={lab.replays} loading={lab.replayLoading} error={lab.replayError} onRun={lab.runReplay} />
      ) : (
        <ReverseStress
          result={lab.reverse}
          loading={lab.reverseLoading}
          error={lab.reverseError}
          currency={input.currency}
          portfolioValue={input.portfolio_value}
          onRun={lab.runReverse}
        />
      )}
    </Card>
  );
}
