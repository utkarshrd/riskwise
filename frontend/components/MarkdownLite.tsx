import type { ReactNode } from "react";
import { slugify } from "@/lib/metric-docs";

/**
 * Renders the small markdown subset used by docs/MARKET_RISK_METHODS.md:
 * headings, paragraphs, bullet lists, fenced code, pipe tables, rules, and **bold** / *italic* / `code`.
 * Headings get slug ids so sections can be linked (e.g. #1-historical-simulation-hs-var).
 */

function inline(text: string, keyBase: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g).filter(Boolean);
  return parts.map((part, i) => {
    const key = `${keyBase}-${i}`;
    if (part.startsWith("**")) return <strong key={key}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`")) {
      return (
        <code key={key} className="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-[0.9em]">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2) return <em key={key}>{part.slice(1, -1)}</em>;
    return part;
  });
}

function splitRow(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

export default function MarkdownLite({ source }: { source: string }) {
  const lines = source.split(/\r?\n/);
  const out: ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const key = `b${i}`;

    if (line.startsWith("```")) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) code.push(lines[i++]);
      i++;
      out.push(
        <pre key={key} className="overflow-x-auto rounded-lg bg-slate-100 dark:bg-slate-800 p-3 text-xs font-mono leading-relaxed">
          {code.join("\n")}
        </pre>,
      );
    } else if (/^#{1,3}\s/.test(line)) {
      const level = line.match(/^#+/)![0].length;
      const text = line.replace(/^#+\s*/, "");
      const id = slugify(text);
      if (level === 1) {
        out.push(<h1 key={key} id={id} className="text-2xl font-bold tracking-tight">{text}</h1>);
      } else if (level === 2) {
        out.push(<h2 key={key} id={id} className="scroll-mt-20 pt-4 text-lg font-semibold">{text}</h2>);
      } else {
        out.push(<h3 key={key} id={id} className="scroll-mt-20 pt-2 text-sm font-semibold">{text}</h3>);
      }
      i++;
    } else if (line.startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        if (!/^\|[\s:|-]+\|?$/.test(lines[i])) rows.push(splitRow(lines[i]));
        i++;
      }
      const [head, ...body] = rows;
      out.push(
        <div key={key} className="overflow-x-auto">
          <table className="w-full text-left text-xs border border-slate-200 dark:border-slate-700">
            <thead className="bg-slate-50 dark:bg-slate-800">
              <tr>{head.map((c, j) => <th key={j} className="px-3 py-2 font-semibold">{inline(c, `${key}h${j}`)}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {body.map((r, ri) => (
                <tr key={ri}>{r.map((c, j) => <td key={j} className="px-3 py-1.5">{inline(c, `${key}r${ri}c${j}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
    } else if (/^\s*[-*]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s/.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*]\s/, ""));
      out.push(
        <ul key={key} className="list-disc pl-5 space-y-1">
          {items.map((t, j) => <li key={j}>{inline(t, `${key}l${j}`)}</li>)}
        </ul>,
      );
    } else if (/^---+$/.test(line.trim())) {
      out.push(<hr key={key} className="border-slate-200 dark:border-slate-800" />);
      i++;
    } else if (line.trim() === "") {
      i++;
    } else {
      const para: string[] = [];
      while (
        i < lines.length &&
        lines[i].trim() !== "" &&
        !/^(```|#{1,3}\s|\||\s*[-*]\s|---+$)/.test(lines[i])
      ) {
        para.push(lines[i++]);
      }
      out.push(<p key={key}>{inline(para.join(" "), key)}</p>);
    }
  }

  return <div className="space-y-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{out}</div>;
}
