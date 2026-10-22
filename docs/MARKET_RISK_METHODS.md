# Market Risk Methodology Reference

Detailed mathematical formulas, assumptions, and academic references for all VaR / ES / backtest methods in RiskWise.

---

## 1. Historical Simulation (HS) VaR

**Formula:**

```
VaR_α = -quantile(L_1, ..., L_T; α)
     where L_t = -R_t  (losses = negative returns)
```

**Scaling to h-day horizon (Basel square-root rule):**

```
VaR_α^h = VaR_α^1 × √h
```

- **Assumptions:** No distributional assumption; returns are i.i.d. within the lookback window.
- **Lookback default:** 252 trading days (≈ 1 calendar year).
- **Implementation:** `numpy.percentile(losses, 100*(1-α))`.
- **Reference:** Hull, J.C. (2015). *Options, Futures, and Other Derivatives* (10th ed.), §22.

---

## 2. Parametric Gaussian VaR

**Formula:**

```
VaR_α = μ_p - z_α × σ_p
```

where:
- `μ_p = w⊤μ` — weighted mean of asset returns
- `σ_p = √(w⊤Σw)` — portfolio standard deviation
- `z_α` — standard normal quantile: 1.645 (95%), 2.326 (99%)

**Scaling:**

```
μ_p^h = h × μ_p
σ_p^h = √h × σ_p
```

- **Assumptions:** Portfolio returns are jointly normally distributed.
- **Implementation:** `scipy.stats.norm.ppf(α) × σ_p - μ_p`.
- **Reference:** J.P. Morgan / Reuters (1996). *RiskMetrics Technical Document* (4th ed.).

---

## 3. Student-t Parametric VaR

**Formula:**

```
VaR_α = μ_p - t_{ν,α} × σ_p × √((ν-2)/ν)
```

- `ν` — degrees of freedom fitted by maximum likelihood on the portfolio's historical return series.
- `t_{ν,α}` — inverse CDF of t(ν) at level α.
- Captures heavier tails than Gaussian; applicable when sample excess kurtosis > 0.

**Implementation:** `scipy.stats.t.fit(returns)` then `scipy.stats.t.ppf(1-α, df=ν)`.

**Reference:** McNeil, A., Frey, R., & Embrechts, P. (2015). *Quantitative Risk Management* (Rev. ed.), §2.3.

---

## 4. EWMA VaR (RiskMetrics λ = 0.94)

**Variance update:**

```
σ²_t = λ σ²_{t-1} + (1-λ) r²_{t-1}
```

**VaR:**

```
VaR_α = μ_p - z_α × σ_T
```

- `λ = 0.94` (daily, as per J.P. Morgan RiskMetrics convention).
- Recent observations receive exponentially higher weight; σ reacts quickly to volatility clusters.
- σ² initialised at the unconditional sample variance over the lookback window.

**Implementation:** `numpy` rolling dot product with geometric weight vector `λ^{T-1}, ..., λ^0`.

**Reference:** J.P. Morgan / Reuters (1996). *RiskMetrics Technical Document*, §5.

---

## 5. GARCH(1,1) VaR

**Variance equation:**

```
σ²_t = ω + α r²_{t-1} + β σ²_{t-1}
```

**Parameters:** Fitted by maximum likelihood assuming normally distributed innovations.

**Stationarity condition:** `α + β < 1`.

**Long-run (unconditional) variance:** `σ̄² = ω / (1 - α - β)`.

**VaR at horizon h:**

```
σ²_{T+h|T} = σ̄² + (α+β)^{h-1}(σ²_{T+1|T} - σ̄²)
VaR_α^h = z_α × σ_{T+h|T}
```

**Implementation:** `arch.arch_model(returns, vol='Garch', p=1, q=1)`.

**Reference:** Bollerslev, T. (1986). Generalized Autoregressive Conditional Heteroskedasticity. *Journal of Econometrics*, 31(3), 307–327.

---

## 6. Cornish-Fisher VaR

**Adjusted quantile:**

```
z_CF = z_α + (z_α² - 1) S/6 + (z_α³ - 3z_α) E/24 - (2z_α³ - 5z_α) S²/36
```

where:
- `S` — portfolio return skewness
- `E` — excess kurtosis
- `z_α` — standard normal quantile

**VaR:**

```
VaR_α = μ_p - z_CF × σ_p
```

- Extends the Gaussian formula with 4th-order Gram-Charlier correction for skewness and excess kurtosis.
- Particularly effective for portfolios with asymmetric return distributions.

**Reference:** Cornish, E.A. & Fisher, R.A. (1938). Moments and Cumulants in the Specification of Distributions. *Revue de l'Institut International de Statistique*, 5(4), 307–320.

---

## 7. Monte Carlo VaR (Cholesky Seeded)

**Algorithm:**

```
1. Estimate Σ from historical returns (capped at lookback window)
2. Cholesky decompose: L L⊤ = Σ
3. Generate M=50,000 standard normal vectors: Z ~ N(0, I_n)
4. Apply Cholesky map: R_sim = L Z + μ (annualised drift scaled to 1 day)
5. Form portfolio PnL: P = w⊤R_sim
6. VaR_α = -quantile(P; 1-α)
```

- **Seed:** Fixed at `seed=42` for deterministic reproducibility.
- **Cholesky stability:** Near-singular Σ clipped via `numpy.linalg.cholesky` on Σ + ε·I.
- **Horizon scaling:** `R_sim^h = L(√h·Z) + h·μ`.

**Reference:** Glasserman, P. (2004). *Monte Carlo Methods in Financial Engineering*. Springer, §2.

---

## 8. Filtered Historical Simulation (FHS)

**Algorithm:**

```
1. Fit GARCH(1,1) to each asset's return series
2. Extract standardised residuals: z_t = r_t / σ_t
3. Resample residuals empirically (non-parametric tail)
4. Re-scale by current GARCH forecast σ_{T+1}: r̃_t = σ_{T+1} × z_t
5. Form portfolio losses; apply empirical quantile
```

- Combines GARCH time-varying volatility with empirical residual distribution.
- Avoids Gaussian tail assumption; preserves observed extreme shocks.

**Reference:** Barone-Adesi, G., Engle, R., & Mancini, L. (2008). A GARCH Option Pricing Model with Filtered Historical Simulation. *Review of Financial Studies*, 21(3), 1223–1258.

---

## 9. Expected Shortfall (CVaR)

**Formula:**

```
ES_α = -E[R | R ≤ -VaR_α]
     = -1/(T(1-α)) × Σ_{R_t ≤ -VaR_α} R_t     (historical)
     = μ - σ × φ(z_α)/(1-α)                     (Gaussian)
```

- ES satisfies the sub-additivity axiom (a coherent risk measure); VaR does not.
- Basel III/IV mandates ES at 97.5% for internal models approach (IMA).

**Reference:** Artzner, P., Delbaen, F., Eber, J.M., & Heath, D. (1999). Coherent Measures of Risk. *Mathematical Finance*, 9(3), 203–228.

---

## 10. Component VaR & Euler Decomposition

**Portfolio VaR:**

```
VaR_p = z_α × σ_p
```

**Component VaR (Euler allocation):**

```
CVaR_i = w_i × Cov(r_i, r_p) / σ_p × z_α
        = w_i × (Σw)_i / σ_p × z_α
```

**Percentage contribution:**

```
%CVaR_i = CVaR_i / VaR_p
```

**Property:** `Σ %CVaR_i = 1` (exact decomposition, Euler's theorem for homogeneous functions).

**Marginal VaR (MVAR):**

```
MVAR_i = ∂VaR_p/∂w_i = (Σw)_i / σ_p × z_α
```

**Reference:** Litterman, R. (1997). Hot Spots and Hedges. *Journal of Portfolio Management*, 24, 52–75.

---

## 11. Kupiec Proportion of Failures (POF) Test

**Hypothesis:**

```
H₀: p = p₀ = 1 - α     (true exception rate equals nominal)
H₁: p ≠ p₀
```

**Likelihood Ratio statistic:**

```
LR_uc = -2 ln[(1-p₀)^(T-x) p₀^x / (1-x/T)^(T-x) (x/T)^x]
      ~ χ²(1) under H₀
```

- `T` — total out-of-sample forecasts; `x` — observed exceptions.
- Reject H₀ at α=0.05 when `LR_uc > 3.841`.

**Reference:** Kupiec, P. (1995). Techniques for Verifying the Accuracy of Risk Measurement Models. *Journal of Derivatives*, 3(2), 73–84.

---

## 12. Christoffersen Independence & Conditional Coverage Tests

**Transition matrix (first-order Markov):**

| | Today: 0 | Today: 1 |
|---|---|---|
| **Yesterday: 0** | n₀₀ | n₀₁ |
| **Yesterday: 1** | n₁₀ | n₁₁ |

```
π̂₀₁ = n₀₁/(n₀₀+n₀₁)     π̂₁₁ = n₁₁/(n₁₀+n₁₁)     π̂ = (n₀₁+n₁₁)/T
```

**Independence LR:**

```
LR_ind = -2 ln[π̂^(n₀₁+n₁₁) (1-π̂)^(n₀₀+n₁₀)] / [π̂₀₁^n₀₁ (1-π̂₀₁)^n₀₀ × π̂₁₁^n₁₁ (1-π̂₁₁)^n₁₀]
       ~ χ²(1) under H₀
```

**Conditional Coverage:**

```
LR_cc = LR_uc + LR_ind ~ χ²(2) under H₀
```

**Reference:** Christoffersen, P. (1998). Evaluating Interval Forecasts. *International Economic Review*, 39(4), 841–862.

---

## 13. Basel BCBS 250-Day Traffic-Light Classification

| Exceptions (x, N=250) | Zone | Capital Multiplier |
|---|---|---|
| 0–4 | 🟢 GREEN | 3.00× |
| 5 | 🟡 YELLOW | 3.40× |
| 6 | 🟡 YELLOW | 3.50× |
| 7 | 🟡 YELLOW | 3.65× |
| 8 | 🟡 YELLOW | 3.75× |
| 9 | 🟡 YELLOW | 3.85× |
| ≥ 10 | 🔴 RED | 4.00× |

**Cumulative probability:** Computed via `scipy.stats.binom.cdf(x, 250, 0.01)` (99% VaR) to quantify the probability of observing x or fewer exceptions by chance.

**Reference:** Basel Committee on Banking Supervision (1996). *Supervisory Framework for the Use of "Backtesting" in Conjunction with the Internal Models Approach to Market Risk Capital Requirements* (BCBS #22).

---

## 14. Performance & Factor Metrics

### Sharpe Ratio (Rf = 0%)

```
SR = μ_ann / σ_ann = (μ_d × 252) / (σ_d × √252) = (μ_d / σ_d) × √252
```

### Sortino Ratio

```
Sortino = μ_ann / σ_down_ann
σ_down = √(1/T × Σ min(R_t, 0)²)
```

### Maximum Drawdown

```
MDD = max_{s≤t}[(Peak_s - Trough_t) / Peak_s]
```

### Beta to Benchmark

```
β = Cov(r_p, r_B) / Var(r_B)
  = Corr(r_p, r_B) × σ_p / σ_B
```

---

## 15. Model Comparison & Selection Score

RiskWise's `/api/v1/market/var/compare` endpoint ranks all 8 VaR methods using a composite score:

```
score = 0.40 × [1 - |exception_rate - p₀| / p₀]   # accuracy
      + 0.25 × kupiec_p_value                        # statistical validity
      + 0.20 × christoffersen_ind_p_value             # independence
      + 0.15 × (1 / basel_capital_multiplier)         # capital efficiency
```

The method with the highest composite score is recommended with a plain-English explanation.

---

*Last updated: 2026-10-22 — RiskWise Tier A upgrade (A1–A6).*
