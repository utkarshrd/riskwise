# RiskWise Credit Risk Model Card

**Generated At:** 2026-10-14T10:10:48.568139+00:00  
**Source Artifacts:** `artifacts/evaluation/model_comparison.json`, `artifacts/evaluation/fairness_audit.json`  
**Active Champion Model Family:** `xgboost`  
**Model Version:** `credit_xgboost_v1`  
**Feature Engineering Strategy:** 21 Currency-Free Behavioral Features (Demographics Excluded)  

---

## 1. Model Overview
- **Model Name:** `credit_xgboost_v1`
- **Model Family:** Gradient Boosted Decision Trees (XGBoost Classifier) with TreeSHAP explainer
- **Calibration:** Isotonic regression calibrated on validation split
- **Target Variable:** `default_payment_next_month` (Binary: 1 = default, 0 = non-default)
- **Primary Objective:** Provide defensible, currency-free relative credit risk ranking, local TreeSHAP attribution, and actionable sensitivity what-if analysis.
- **Dataset Provenance:** UCI Machine Learning Repository - Default of Credit Card Clients (Taiwan, 2005). 30,000 observations.
- **Class Imbalance Handling:** Algorithmic weighting (`scale_pos_weight = 3.52` on training split).

---

## 2. Evaluation Protocol & Candidate Comparison
All models evaluated using a strict **70/15/15** Stratified Split:
- **Train partition:** 21,000 records
- **Validation partition:** 4,500 records (used for calibration selection, decision threshold optimization, and risk band cutoffs)
- **Held-out test partition:** 4,500 records (evaluated strictly once)

### Candidate Comparison on Defensible Feature Set (Engineered, No Demographics)

| Candidate Model Family | ROC-AUC | PR-AUC | Recall | Precision | F1-Score | Brier Score | Calib Method | Decision Threshold |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Logistic Regression** | 0.7456 | 0.4912 | 0.5020 | 0.5400 | 0.5203 | 0.1426 | isotonic | 0.32 |
| **Random Forest** | 0.7753 | 0.5473 | 0.5723 | 0.5108 | 0.5398 | 0.1359 | isotonic | 0.28 |
| **XGBoost (Champion)** | **0.7757** | **0.5512** | **0.5522** | **0.5273** | **0.5395** | **0.1358** | **isotonic** | **0.30** |

### Champion Confusion Matrix (Test Partition: 4,500 records)
```
                  Predicted Non-Default (0)   Predicted Default (1)
Actual Non-Default (0)          3011                       493
Actual Default (1)              446                        550
```

---

## 3. Feature Suite Progression & Demographic Exclusion

To ensure defensibility, fair lending compliance, and currency invariance, the models were evaluated across three progressive feature configurations:

| Feature Suite | Model Family | ROC-AUC | PR-AUC | Recall | Precision | F1-Score | Brier Score |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Original Raw Features (23 cols)** | Logistic Regression | 0.7183 | 0.4882 | 0.4759 | 0.5290 | 0.5011 | 0.1436 |
| | Random Forest | 0.7762 | 0.5487 | 0.6145 | 0.4968 | 0.5494 | 0.1362 |
| | XGBoost | 0.7806 | 0.5558 | 0.5924 | 0.5021 | 0.5435 | 0.1351 |
| **2. Engineered WITH Demographics (25 cols)** | Logistic Regression | 0.7489 | 0.4925 | 0.5110 | 0.5302 | 0.5204 | 0.1422 |
| | Random Forest | 0.7762 | 0.5520 | 0.6024 | 0.4819 | 0.5355 | 0.1358 |
| | XGBoost | 0.7796 | 0.5548 | 0.5944 | 0.4954 | 0.5404 | 0.1354 |
| **3. Engineered WITHOUT Demographics (21 cols)** | Logistic Regression | 0.7456 | 0.4912 | 0.5020 | 0.5400 | 0.5203 | 0.1426 |
| | Random Forest | 0.7753 | 0.5473 | 0.5723 | 0.5108 | 0.5398 | 0.1359 |
| | **XGBoost (Production Champion)** | **0.7757** | **0.5512** | **0.5522** | **0.5273** | **0.5395** | **0.1358** |

### Demographic Exclusion Justification
- **Legal & Regulatory Compliance:** Equal Credit Opportunity Act (ECOA / Reg B) and RBI Fair Practices Code prohibit using sex, marital status, or educational attainment in credit scoring.
- **Defensibility of Age Exclusion:** While age is sometimes treated as non-protected under strict limitations, retaining AGE contributed negligible discriminative lift while creating youth disparagement (<25 approval disparity). Excluding AGE produces a purely behavioral model based on repayment history, credit utilisation, and payment discipline.
- **Performance Invariance:** Removing protected demographic attributes incurred negligible degradation in discriminative ranking power (ROC-AUC 0.7796 -> 0.7757) while completely eliminating direct demographic disparity.

---

## 4. Fair Lending & Demographic Parity Audit

Evaluated on the held-out test partition (4,500 records) at the production operating threshold ($\tau = 0.3$):

### 4.1 Subgroup Performance Metrics

| Demographic Slice | Subgroup | Sample Size | ROC-AUC | Approval Rate | Base Default Rate | Default Recall |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Sex** | Male (SEX=1) | 1766 | 0.7510 | 75.08% | 25.37% | 54.02% |
| | Female (SEX=2) | 2734 | 0.7932 | 77.94% | 20.04% | 56.20% |
| **Education** | Graduate School | 1580 | 0.7738 | 79.68% | 20.25% | 52.50% |
| | University | 2086 | 0.7887 | 75.26% | 22.87% | 57.65% |
| | High School | 766 | 0.7344 | 73.76% | 25.72% | 53.81% |
| **Marriage** | Married | 2063 | 0.7731 | 76.59% | 24.14% | 54.02% |
| | Single | 2383 | 0.7794 | 77.13% | 20.52% | 56.03% |
| **Age Band** | <25 | 383 | 0.7710 | 69.45% | 25.33% | 59.79% |
| | 25-34 | 1948 | 0.7882 | 77.87% | 19.87% | 56.33% |
| | 35-49 | 1758 | 0.7631 | 77.82% | 22.47% | 53.92% |
| | 50+ | 411 | 0.7733 | 74.45% | 28.47% | 52.14% |

### 4.2 Disparate Impact Ratios (Four-Fifths Rule Compliance)
The Disparate Impact Ratio (DIR) evaluates approval rates across protected groups against reference groups:

$$\text{DIR} = \frac{\text{Approval Rate}_{\text{Adverse Group}}}{\text{Approval Rate}_{\text{Reference Group}}}$$

Under the Equal Employment Opportunity Commission (EEOC) and Consumer Financial Protection Bureau (CFPB) four-fifths rule, a selection rate for any group that is less than four-fifths (80%, or $0.80$) of the rate for the group with the highest rate constitutes evidence of adverse impact.

| Demographic Dimension | Comparison Pair | Computed DIR | Threshold (80% Rule) | Audit Result |
|---|---|:---:|:---:|:---:|
| **Sex** | Female vs. Male | **1.04** | $\ge 0.80$ | **PASS** (Compliant) |
| **Education** | High School vs. Graduate School | **0.93** | $\ge 0.80$ | **PASS** (Compliant) |
| **Marriage** | Single vs. Married | **1.01** | $\ge 0.80$ | **PASS** (Compliant) |
| **Age Band** | <25 vs. 25-34 Reference | **0.89** | $\ge 0.80$ | **PASS** (Compliant) |

**Overall Compliance Status:** All demographic slices satisfy the Four-Fifths rule with zero violation of fair lending parity.

---

## 5. Calibration & Operating Thresholds
- **Calibration Method:** Isotonic regression fitted on validation split.
- **Uncalibrated Validation Brier:** 0.1800
- **Calibrated Validation Brier:** 0.1365
- **Brier Improvement:** +0.0435
- **Decision Threshold ($\tau^*$):** 0.30 (chosen via validation $F_1$ optimization)
- **Risk Band Cutoffs:**
  - Low Risk: < 0.0924
  - Moderate Risk: 0.0924 - 0.1482
  - Elevated Risk: 0.1482 - 0.3822
  - High Risk: >= 0.3822

---

## 6. Responsible Use & Proxy Data Limitations
1. **Proxy Benchmark:** The dataset represents Taiwanese credit card clients from 2005. It is NOT representative of present-day Indian retail borrowers.
2. **No CIBIL Equivalence:** RiskWise relative risk ranking is an educational benchmark indicator, not an Indian bureau score.
3. **Actionable What-If Guardrails:** Protected attributes (`SEX`, `EDUCATION`, `MARRIAGE`, `AGE`) are strictly non-modifiable. Counterfactual sensitivity is strictly restricted to borrower-controllable factors (repayment amounts, utilisation, delinquency remediation).
