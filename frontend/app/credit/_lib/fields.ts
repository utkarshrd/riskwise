import { Building2, Search, ShieldCheck, UserCheck, type LucideIcon } from "lucide-react";

export type FeatureValues = Record<string, string | number>;

interface BaseField {
  key: string;
  label: string;
  /** Value shown when the profile has no value for this feature yet. */
  fallback: string | number;
}

export interface NumberField extends BaseField {
  kind: "number";
  fallback: number;
  min?: number;
  max?: number;
  step?: number;
}

export interface SelectField extends BaseField {
  kind: "select";
  options: { value: string | number; label: string }[];
}

export type Field = NumberField | SelectField;

const num = (key: string, label: string, fallback: number, opts: Partial<NumberField> = {}): NumberField => ({
  kind: "number",
  key,
  label,
  fallback,
  ...opts,
});

const select = (key: string, label: string, fallback: string | number, options: SelectField["options"]): SelectField => ({
  kind: "select",
  key,
  label,
  fallback,
  options,
});

const flag = (key: string, label: string, fallback: number, on: string, off: string) =>
  select(key, label, fallback, [
    { value: 1, label: `1 (${on})` },
    { value: 0, label: `0 (${off})` },
  ]);

const enquiredProduct = [
  { value: "PL", label: "PL (Personal Loan)" },
  { value: "CC", label: "CC (Credit Card)" },
  { value: "HL", label: "HL (Home Loan)" },
  { value: "AL", label: "AL (Auto Loan)" },
  { value: "ConsumerLoan", label: "Consumer Loan" },
  { value: "others", label: "Others" },
];

export interface FieldGroup {
  title: string;
  icon: LucideIcon;
  /** Tailwind classes for the section heading colour (light and dark). */
  accent: string;
  columns: "sm:grid-cols-2" | "sm:grid-cols-3";
  fields: Field[];
}

export const FIELD_GROUPS: FieldGroup[] = [
  {
    title: "1. Repayment & Delinquency Behavior",
    icon: ShieldCheck,
    accent: "text-indigo-600 dark:text-indigo-400",
    columns: "sm:grid-cols-2",
    fields: [
      num("Tot_Missed_Pmnt", "Total Missed Payments (All Time)", 0, { min: 0, max: 20 }),
      num("num_times_60p_dpd", "Instances of 60+ Days Past Due (DPD)", 0, { min: 0, max: 10 }),
      num("recent_level_of_deliq", "Recent Level of Delinquency Code", 0, { min: 0, max: 5 }),
      num("time_since_recent_payment", "Months Since Most Recent Payment", 1, { min: 0, max: 60 }),
    ],
  },
  {
    title: "2. Credit Accounts & Trade Lines",
    icon: Building2,
    accent: "text-blue-600 dark:text-blue-400",
    columns: "sm:grid-cols-3",
    fields: [
      num("Secured_TL", "Secured Trade Lines", 0, { min: 0 }),
      num("Unsecured_TL", "Unsecured Trade Lines", 1, { min: 0 }),
      num("Home_TL", "Home Loan Accounts", 0, { min: 0 }),
      num("PL_TL", "Personal Loans (PL)", 1, { min: 0 }),
      num("Age_Oldest_TL", "Age of Oldest Account (Months)", 48, { min: 1 }),
      num("Age_Newest_TL", "Age of Newest Account (Months)", 6, { min: 1 }),
    ],
  },
  {
    title: "3. Inquiries & Bureau Activity",
    icon: Search,
    accent: "text-amber-600 dark:text-amber-400",
    columns: "sm:grid-cols-3",
    fields: [
      num("enq_L3m", "Enquiries in Last 3 Months", 0, { min: 0, max: 20 }),
      num("PL_enq_L12m", "PL Enquiries in Last 12 Months", 0, { min: 0 }),
      num("time_since_recent_enq", "Months Since Recent Enquiry", 6, { min: 0 }),
    ],
  },
  {
    title: "4. Borrower Profile & Employment",
    icon: UserCheck,
    accent: "text-emerald-600 dark:text-emerald-400",
    columns: "sm:grid-cols-3",
    fields: [
      num("NETMONTHLYINCOME", "Net Monthly Income (INR)", 45000, { min: 5000, step: 1000 }),
      num("Time_With_Curr_Empr", "Employer Tenure (Months)", 36, { min: 1 }),
      select("MARITALSTATUS", "Marital Status", "Married", [
        { value: "Married", label: "Married" },
        { value: "Single", label: "Single" },
      ]),
      select("EDUCATION", "Education Level", "GRADUATE", [
        { value: "GRADUATE", label: "Graduate" },
        { value: "POST-GRADUATE", label: "Post-Graduate" },
        { value: "UNDER GRADUATE", label: "Undergraduate" },
        { value: "12TH", label: "12th Standard" },
        { value: "SSC", label: "SSC (10th)" },
        { value: "PROFESSIONAL", label: "Professional" },
        { value: "OTHERS", label: "Others" },
      ]),
      select("GENDER", "Borrower Gender", "M", [
        { value: "M", label: "Male (M)" },
        { value: "F", label: "Female (F)" },
      ]),
    ],
  },
];

const ratio = { min: 0, max: 1, step: 0.05 };

export const ADVANCED_FIELDS: Field[] = [
  num("pct_tl_open_L6M", "Share of Trade Lines Opened (6M)", 0, ratio),
  num("pct_tl_closed_L6M", "Share of Trade Lines Closed (6M)", 0, ratio),
  num("Tot_TL_closed_L12M", "Trade Lines Closed (12M)", 0, { min: 0 }),
  num("pct_tl_closed_L12M", "Share of Trade Lines Closed (12M)", 0, ratio),
  num("CC_TL", "Credit Card Accounts", 1, { min: 0 }),
  num("Other_TL", "Other Accounts", 0, { min: 0 }),
  num("max_recent_level_of_deliq", "Max Recent Delinquency Level", 0, { min: 0, max: 5 }),
  num("num_deliq_6_12mts", "Delinquencies (6-12 Months)", 0, { min: 0 }),
  num("num_std_12mts", "Standard Payment Months (12M)", 12, { min: 0, max: 12 }),
  num("num_sub", "Substandard Accounts", 0, { min: 0 }),
  num("num_sub_6mts", "Substandard Accounts (6M)", 0, { min: 0 }),
  num("num_sub_12mts", "Substandard Accounts (12M)", 0, { min: 0 }),
  num("num_dbt", "Doubtful Accounts", 0, { min: 0 }),
  num("num_dbt_12mts", "Doubtful Accounts (12M)", 0, { min: 0 }),
  num("num_lss", "Loss Accounts", 0, { min: 0 }),
  num("CC_enq_L12m", "Credit Card Enquiries (12M)", 0, { min: 0 }),
  flag("CC_Flag", "Credit Card Flag", 1, "Active Card", "No Card"),
  flag("PL_Flag", "Personal Loan Flag", 0, "Active PL", "No PL"),
  flag("HL_Flag", "Home Loan Flag", 0, "Active HL", "No HL"),
  flag("GL_Flag", "Gold Loan Flag", 0, "Active GL", "No GL"),
  num("pct_PL_enq_L6m_of_ever", "Share of PL Enquiries in Last 6M (of all ever)", 0, ratio),
  num("pct_CC_enq_L6m_of_ever", "Share of CC Enquiries in Last 6M (of all ever)", 0, ratio),
  select("last_prod_enq2", "Last Enquired Product", "PL", enquiredProduct),
  select("first_prod_enq2", "First Enquired Product", "CC", [...enquiredProduct.slice(1, 2), enquiredProduct[0], ...enquiredProduct.slice(2)]),
];

/** Readable names for every model feature, used by the SHAP panel. */
const ALL_FIELDS: Field[] = [...FIELD_GROUPS.flatMap((g) => g.fields), ...ADVANCED_FIELDS];
const LABELS: Record<string, string> = Object.fromEntries(ALL_FIELDS.map((f) => [f.key, f.label]));

/** Feature names arrive from the model as e.g. `num__Tot_Missed_Pmnt` or `cat__MARITALSTATUS_Married`. */
export function featureLabel(modelName: string): string {
  const raw = modelName.split("__").pop() || modelName;
  if (LABELS[raw]) return LABELS[raw];
  const prefixed = ALL_FIELDS.find((f) => raw.startsWith(`${f.key}_`));
  if (prefixed) return `${prefixed.label}: ${raw.slice(prefixed.key.length + 1)}`;
  return raw;
}

/** Used until the API returns its reference profiles. */
export const DEFAULT_FEATURES: FeatureValues = Object.fromEntries(ALL_FIELDS.map((f) => [f.key, f.fallback]));
