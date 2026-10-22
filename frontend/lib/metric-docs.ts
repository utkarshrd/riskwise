/**
 * Glossary tying every metric shown in the UI to its section in docs/MARKET_RISK_METHODS.md.
 *
 * `heading` must match a heading in that file exactly (without the leading #). The backend test
 * `test_metric_docs_headings.py` fails if a heading here no longer exists in the document.
 */

export const METHODS_PATH = "/methodology/market-risk";

/** GitHub-style heading slug; also used by the methods page to build anchor ids. */
export function slugify(heading: string): string {
  return heading
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-");
}

export function methodsHref(heading: string): string {
  return `${METHODS_PATH}#${slugify(heading)}`;
}

interface MetricDoc {
  label: string;
  summary: string;
  heading: string;
}

export const METRIC_DOCS = {
  historical_var: {
    label: "Historical VaR",
    summary:
      "The loss that was exceeded on only 5% (95% VaR) or 1% (99% VaR) of days in the lookback window, read straight from the observed returns.",
    heading: "1. Historical Simulation (HS) VaR",
  },
  parametric_var: {
    label: "Parametric (Gaussian) VaR",
    summary: "VaR assuming daily returns are normally distributed, using the sample mean and standard deviation.",
    heading: "2. Parametric Gaussian VaR",
  },
  student_t_var: {
    label: "Student-t VaR",
    summary: "Parametric VaR with a fat-tailed Student-t distribution, so extreme days are more likely than under a normal curve.",
    heading: "3. Student-t Parametric VaR",
  },
  ewma_var: {
    label: "EWMA VaR",
    summary: "VaR from an exponentially weighted volatility (RiskMetrics, decay 0.94) that reacts faster to recent moves.",
    heading: "4. EWMA VaR (RiskMetrics λ = 0.94)",
  },
  garch_var: {
    label: "GARCH(1,1) VaR",
    summary: "VaR from a volatility forecast that models volatility clustering.",
    heading: "5. GARCH(1,1) VaR",
  },
  cornish_fisher_var: {
    label: "Cornish-Fisher VaR",
    summary: "Gaussian VaR adjusted for the skewness and excess kurtosis seen in the returns.",
    heading: "6. Cornish-Fisher VaR",
  },
  monte_carlo_var: {
    label: "Monte Carlo VaR",
    summary: "VaR from seeded simulated returns that keep the correlations between holdings.",
    heading: "7. Monte Carlo VaR (Cholesky Seeded)",
  },
  fhs_var: {
    label: "Filtered Historical Simulation",
    summary: "Historical returns rescaled by current volatility, combining the empirical shape with a current risk level.",
    heading: "8. Filtered Historical Simulation (FHS)",
  },
  expected_shortfall: {
    label: "Expected Shortfall (CVaR)",
    summary: "The average loss on the days when the loss exceeds the VaR threshold. It tells you how bad the tail is, not just where it starts.",
    heading: "9. Expected Shortfall (CVaR)",
  },
  component_var: {
    label: "Risk contribution (Component VaR)",
    summary: "How much of the portfolio VaR each holding is responsible for. The contributions add up to the total.",
    heading: "10. Component VaR & Euler Decomposition",
  },
  kupiec: {
    label: "Kupiec POF test",
    summary: "Checks whether the number of days the loss beat the VaR matches what the confidence level predicts.",
    heading: "11. Kupiec Proportion of Failures (POF) Test",
  },
  christoffersen: {
    label: "Christoffersen tests",
    summary: "Checks that VaR breaches are not bunched together (independence), and combined with Kupiec gives conditional coverage.",
    heading: "12. Christoffersen Independence & Conditional Coverage Tests",
  },
  basel: {
    label: "Basel traffic light",
    summary: "Regulatory zone (green, yellow, red) from the count of 99% VaR breaches over 250 days; it sets the capital multiplier.",
    heading: "13. Basel BCBS 250-Day Traffic-Light Classification",
  },
  sharpe: {
    label: "Sharpe ratio",
    summary: "Annualised return above a fixed risk-free proxy (6% INR, 5% USD) per unit of annualised volatility.",
    heading: "Sharpe Ratio",
  },
  sortino: {
    label: "Sortino ratio",
    summary: "Like Sharpe, but only downside volatility counts as risk.",
    heading: "Sortino Ratio",
  },
  max_drawdown: {
    label: "Maximum drawdown",
    summary: "The largest peak-to-trough fall in portfolio value over the window.",
    heading: "Maximum Drawdown",
  },
  beta: {
    label: "Beta",
    summary: "How much the portfolio moves for a 1% move in the benchmark. Above 1 means it amplifies the benchmark.",
    heading: "Beta to Benchmark",
  },
  model_selection: {
    label: "Model selection score",
    summary: "Composite ranking of the VaR methods from exception rate, Kupiec and Christoffersen p-values and Basel capital.",
    heading: "15. Model Comparison & Selection Score",
  },
  loss_convention: {
    label: "Loss convention",
    summary: "Losses are positive numbers, so a 2% VaR means a 2% loss threshold.",
    heading: "Loss Convention",
  },
  annualized_volatility: {
    label: "Annualized volatility",
    summary: "Standard deviation of daily returns scaled by the square root of 252 trading days.",
    heading: "Annualized Volatility",
  },
  mean_daily_return: {
    label: "Mean daily return",
    summary: "The average daily portfolio return over the window, with weights held constant.",
    heading: "Mean Daily Return",
  },
  cumulative_return: {
    label: "Cumulative return",
    summary: "Compounded portfolio return over the window, drawn against the benchmark over the same dates.",
    heading: "Cumulative Return and Drawdown Series",
  },
  stress_replay: {
    label: "Named event replay",
    summary: "What each holding actually did between two fixed dates of a real market event, weighted by the portfolio. Holdings without prices are skipped and listed.",
    heading: "Named Event Replay",
  },
  reverse_stress: {
    label: "Reverse stress",
    summary: "Works backwards from a loss you pick to the market fall that would cause it, using each holding's beta to the benchmark.",
    heading: "Reverse Stress",
  },
  correlation: {
    label: "Correlation",
    summary: "Pearson correlation of daily returns between each pair of holdings. High values mean less diversification.",
    heading: "Correlation Matrix",
  },
} as const satisfies Record<string, MetricDoc>;

export type MetricKey = keyof typeof METRIC_DOCS;

/** Maps the API's var_method value to its glossary entry. */
export const VAR_METHOD_METRIC: Record<string, MetricKey> = {
  historical: "historical_var",
  gaussian: "parametric_var",
  parametric: "parametric_var",
  student_t: "student_t_var",
  ewma: "ewma_var",
  garch: "garch_var",
  cornish_fisher: "cornish_fisher_var",
  monte_carlo: "monte_carlo_var",
  fhs: "fhs_var",
};
