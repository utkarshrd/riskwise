import { readFile } from "node:fs/promises";
import path from "node:path";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import MarkdownLite from "@/components/MarkdownLite";
import { Alert } from "@/components/ui";

export const metadata = { title: "Market Risk Methods — RiskWise" };

// The reference lives in the repo's docs folder, one level above the frontend app.
const METHODS_FILE = path.join(process.cwd(), "..", "docs", "MARKET_RISK_METHODS.md");

async function loadMethods(): Promise<string | null> {
  "use cache";
  try {
    return await readFile(METHODS_FILE, "utf-8");
  } catch {
    return null;
  }
}

export default async function MarketRiskMethodsPage() {
  const source = await loadMethods();

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <Link
        href="/methodology"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline"
      >
        <ArrowLeft className="w-3.5 h-3.5" /> Methodology & Disclosures
      </Link>
      {source ? (
        <article className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 sm:p-8">
          <MarkdownLite source={source} />
        </article>
      ) : (
        <Alert tone="warning" title="Methods reference not available">
          <code>docs/MARKET_RISK_METHODS.md</code> could not be read from this deployment. It is read from the
          repository&apos;s docs folder next to the frontend, so it is missing when only the frontend is packaged.
        </Alert>
      )}
    </div>
  );
}
