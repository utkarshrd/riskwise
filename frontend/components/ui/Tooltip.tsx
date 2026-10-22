"use client";

import { useId, useState, type ReactNode } from "react";
import Link from "next/link";
import { Info } from "lucide-react";
import { METRIC_DOCS, methodsHref, type MetricKey } from "@/lib/metric-docs";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  /** Which edge of the trigger the popover lines up with; keeps it on screen near viewport edges. */
  align?: "start" | "end";
}

/** Hover, focus or tap to open. The popover is a child of the wrapper, so links inside stay clickable. */
export function Tooltip({ content, children, align = "start" }: TooltipProps) {
  const id = useId();
  const [open, setOpen] = useState(false);

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onBlur={() => setOpen(false)}
    >
      <button
        type="button"
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        className="inline-flex items-center rounded-full text-slate-400 hover:text-indigo-500 focus-visible:text-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        {children}
      </button>
      {open && (
        <span
          role="tooltip"
          id={id}
          className={`absolute top-full z-50 mt-1.5 w-64 max-w-[calc(100vw-2rem)] rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3 text-left text-[11px] font-normal normal-case tracking-normal leading-relaxed text-slate-700 dark:text-slate-200 shadow-lg ${
            align === "end" ? "right-0" : "left-0"
          }`}
        >
          {content}
        </span>
      )}
    </span>
  );
}

interface MetricInfoProps {
  metric: MetricKey;
  align?: "start" | "end";
}

/** (i) icon whose tooltip explains a metric and links to its section in the methodology reference. */
export function MetricInfo({ metric, align = "start" }: MetricInfoProps) {
  const doc = METRIC_DOCS[metric];
  return (
    <Tooltip
      align={align}
      content={
        <>
          <span className="block font-semibold text-slate-900 dark:text-slate-100">{doc.label}</span>
          <span className="block mt-1">{doc.summary}</span>
          <Link
            href={methodsHref(doc.heading)}
            className="mt-2 inline-block font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            Method details →
          </Link>
        </>
      }
    >
      <Info className="w-3.5 h-3.5" aria-label={`About ${doc.label}`} />
    </Tooltip>
  );
}
