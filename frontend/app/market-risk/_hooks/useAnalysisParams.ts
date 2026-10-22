"use client";

import { useState } from "react";

/** Risk-engine settings the user picks next to the portfolio. */
export function useAnalysisParams() {
  const [lookbackDays, setLookbackDays] = useState(252);
  const [returnMethod, setReturnMethod] = useState("simple");
  const [varMethod, setVarMethod] = useState("historical");
  const [horizonDays, setHorizonDays] = useState(1);

  return { lookbackDays, returnMethod, varMethod, horizonDays, setLookbackDays, setReturnMethod, setVarMethod, setHorizonDays };
}

export type AnalysisParams = ReturnType<typeof useAnalysisParams>;
