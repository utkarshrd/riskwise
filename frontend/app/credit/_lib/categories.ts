export interface CategoryStyle {
  chip: string;
  text: string;
  border: string;
  panel: string;
  bar: string;
}

const STYLES: Record<string, CategoryStyle> = {
  P1: {
    chip: "bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400",
    text: "text-emerald-600 dark:text-emerald-400",
    border: "border-emerald-300 dark:border-emerald-600/40",
    panel: "bg-emerald-50/60 dark:bg-emerald-950/30",
    bar: "bg-emerald-500",
  },
  P2: {
    chip: "bg-blue-100 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400",
    text: "text-blue-600 dark:text-blue-400",
    border: "border-blue-300 dark:border-blue-600/40",
    panel: "bg-blue-50/60 dark:bg-blue-950/30",
    bar: "bg-blue-500",
  },
  P3: {
    chip: "bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400",
    text: "text-amber-600 dark:text-amber-400",
    border: "border-amber-300 dark:border-amber-600/40",
    panel: "bg-amber-50/60 dark:bg-amber-950/30",
    bar: "bg-amber-500",
  },
  P4: {
    chip: "bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400",
    text: "text-rose-600 dark:text-rose-400",
    border: "border-rose-300 dark:border-rose-600/40",
    panel: "bg-rose-50/60 dark:bg-rose-950/30",
    bar: "bg-rose-500",
  },
};

/** P1–P4 are the dataset's own relative-risk tiers, not regulated score bands. */
export function categoryStyle(category: string): CategoryStyle {
  return STYLES[category] ?? STYLES.P4;
}
