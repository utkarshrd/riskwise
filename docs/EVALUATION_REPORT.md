# RiskWise Technical Evaluation Report

**Generated:** 2026-10-21T19:20:33.980562+00:00
**Platform Version:** RiskWise v3.1.0 (Indian Credit + Market Risk)
**Standard:** REAL and WIRED — All figures computed from serialized artifacts, real market snapshots, and seeded runs.

---

## 1. Credit Risk Intelligence Benchmark

### 1.1 Dataset Provenance & Split Protocol
- **Dataset:** Indian Banking Credit Risk Dataset (merged External CIBIL + Internal Bank records)
- **Source Files:** `Dataset/External_Cibil_Dataset.xlsx` + `Dataset/Internal_Bank_Dataset.xlsx` merged on `PROSPECTID`
- **Total Observations:** 51,336 merged borrower records
- **Target Variable:** `Approved_Flag` (4-class: P1 = Lowest Risk, P2 = Standard, P3 = Elevated, P4 = Highest Risk)
- **Split Strategy:** 70% train / 15% validation / 15% test, stratified on target, `random_state=42`
- **Leakage Prevention:** `IndianCreditPreprocessor` fitted strictly on training partition.
- **Class Distribution (Test Set):** P1=871, P2=4830, P3=1118, P4=882

### 1.2 Champion Selection: Target Leakage Study
> [!IMPORTANT]
> The `Credit_Score` column from External CIBIL is the output of the bureau's own risk model and directly encodes the target `Approved_Flag`. The `xgboost_with_credit_score` variant achieves ROC-AUC **0.9999** (near-perfect) — confirming target leakage. This variant is **DISQUALIFIED**. The champion is `xgboost` (42 features, NO `Credit_Score`) with ROC-AUC **0.9275**.

| Variant | Features | ROC-AUC (OvR) | Macro-F1 | Status |
|---|:---:|:---:|:---:|:---:|
| Majority Baseline | — | 0.5000 | 0.1927 | Baseline |
| Logistic Regression | 42 | 0.8835 | 0.6080 | Candidate |
| **XGBoost (Champion)** | **42** | **0.9275** | **0.6780** | **CHAMPION** |
| XGBoost (With Credit_Score) | 43 | 0.9999 | 0.9903 | DISQUALIFIED (leakage) |

### 1.3 Champion Model Performance
- **ROC-AUC (Macro OvR):** 0.9275
- **Macro-F1:** 0.6780
- **Weighted-F1:** 0.7679
- **Accuracy:** 0.7852
- **Log Loss:** 0.4882

#### Per-Class Metrics (Champion)
| Class | Support | Precision | Recall | F1 |
|---|:---:|:---:|:---:|:---:|
| P1 | 871 | 0.7948 | 0.7692 | 0.7818 |
| P2 | 4830 | 0.8302 | 0.9234 | 0.8743 |
| P3 | 1118 | 0.4533 | 0.2603 | 0.3307 |
| P4 | 882 | 0.7417 | 0.7098 | 0.7254 |

### 1.4 Fair Lending Audit
Threshold: 0.50
- Gender DIR (Female/Male): 1.0048
- Marital Status DIR (Single/Married): 0.8705
- Education DIR (SSC/Graduate): 1.034
- Four-Fifths Rule Compliant: True

---

## 2. Market Risk & VaR Validation Results

### 2.1 Primary Portfolio (INR: 50% NIFTYBEES.NS, 50% RELIANCE.NS)
- **Observations:** 249 trading days (2025-10-06 to 2026-10-09)
- **Annualized Volatility:** 15.13%
- **Historical VaR (95%):** 1.72%
- **Parametric VaR (95%):** 1.61%
- **CVaR/ES (95%):** 2.07%
- **Maximum Drawdown:** 20.12%

### 2.2 Secondary Portfolio (USD: 60% SPY, 40% AAPL)
- **Observations:** 249 trading days (2025-10-15 to 2026-10-13)
- **Annualized Volatility:** 14.27%
- **Historical VaR (95%):** 1.26%
- **Parametric VaR (95%):** 1.38%
- **CVaR/ES (95%):** 1.88%
- **Maximum Drawdown:** 9.48%

### 2.3 Rolling VaR Validation (Lookback: 100 days)

| Asset | Currency | Forecasts | Exceptions | Observed Rate | Expected Rate | Kupiec LR | p-value | Decision |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| NIFTYBEES.NS | INR | 392 | 26 | 6.63% | 5.00% | 2.0041 | 0.1569 | PASSED |
| SPY | USD | 400 | 24 | 6.00% | 5.00% | 0.7937 | 0.3730 | PASSED |

---

## 3. Known Limitations & Disclosures
1. **Indian Banking Dataset:** Outputs are relative risk rankings (P1-P4) and must not be used as standalone underwriting decisions.
2. **Target Leakage (Credit_Score):** Production champion explicitly excludes Credit_Score. See Section 1.2.
3. **Point-in-Time Market Snapshots:** Downloaded historical closes via Yahoo Finance with documented retrieval timestamps.
4. **VaR Caveat:** Extreme tail losses under black swan events can exceed the VaR bound.
5. **No Trading Strategy Support:** Technical indicator backtesting is strictly out of scope.
