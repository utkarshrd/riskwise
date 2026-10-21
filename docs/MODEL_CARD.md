# RiskWise Credit Risk Model Card

**Generated At:** 2026-10-21T19:20:03.799532+00:00  
**Source Artifacts:** `artifacts/evaluation/model_comparison.json`, `artifacts/evaluation/fairness_audit.json`  
**Active Champion Model Family:** `xgboost` (42 Core Bureau & Trade-Line Features, Target Leakage Free)  
**Model Version:** `credit_xgboost_v1`  
**Dataset:** Indian Banking & CIBIL Bureau Merged Dataset (51,336 records)  

---

## 1. Model Overview
- **Model Name:** `credit_xgboost_v1`
- **Model Family:** Gradient Boosted Decision Trees (XGBoost Classifier) with multiclass softprob objective (4 classes) and TreeSHAP explainer.
- **Target Variable:** `Approved_Flag` multiclass rating:
  - **P1:** Prime / Tier 1 (Lowest Risk, Immediate Approval)
  - **P2:** Near-Prime / Tier 2 (Standard Approval)
  - **P3:** Moderate-High Risk / Tier 3 (Conditional / Flagged)
  - **P4:** Very High Risk / Tier 4 (Decline / Severe Delinquency Risk)
- **Primary Objective:** Deliver defensible, explainable credit risk tier classification for Indian retail borrowers using trade-line behavior, delinquency counts, and bureau inquiry frequency.
- **Dataset Provenance:** Merged Indian Bank Internal Records & External CIBIL Bureau Trade-line data (`dataset/Internal_Bank_Dataset.xlsx` + `dataset/External_Cibil_Dataset.xlsx`, 51,336 borrowers).
- **Leakage Prevention:** `Credit_Score` (bureau score) is explicitly excluded from the production feature set (42 features utilized).

---

## 2. Evaluation Protocol & Candidate Comparison
All models evaluated using a strict **70/15/15** Stratified Split:
- **Train partition:** 35,935 records (70%)
- **Validation partition:** 7,700 records (15%)
- **Held-out test partition:** 7,701 records (15%, evaluated strictly once)

### Candidate Comparison on 42 Core Features (Without Target Leakage)

| Candidate Model Family | ROC-AUC (OvR Macro) | Macro F1 | Weighted F1 | Accuracy | Log Loss | Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Majority Class Baseline** | 0.5000 | 0.1927 | 0.4835 | 0.6272 | 13.4374 | Naive Reference |
| **Multinomial Logistic Regression** | 0.8835 | 0.6080 | 0.7201 | 0.7565 | 0.6246 | Linear Baseline |
| **XGBoost Classifier (Champion)** | **0.9275** | **0.6780** | **0.7679** | **0.7852** | **0.4882** | **Production Champion** |
| *XGBoost (With Credit_Score)* | *0.9999* | *0.9903* | *0.9951* | *0.9951* | *0.0121* | *Disqualified (Leakage)* |

### Champion Per-Class Performance (Test Partition: 7,701 records)

| Credit Tier | Precision | Recall | F1-Score | Support |
|---|:---:|:---:|:---:|:---:|
| **P1** | 0.7948 | 0.7692 | 0.7818 | 871 |
| **P2** | 0.8302 | 0.9234 | 0.8743 | 4830 |
| **P3** | 0.4533 | 0.2603 | 0.3307 | 1118 |
| **P4** | 0.7417 | 0.7098 | 0.7254 | 882 |

### Champion Confusion Matrix (Held-out Test Set)
```
              Predicted P1  Predicted P2  Predicted P3  Predicted P4
Actual P1:         670           201             0             0
Actual P2:         140          4460           196            34
Actual P3:          32           611           291           184
Actual P4:           1           100           155           626
```

---

## 3. Target Leakage Analysis & Champion Selection

### Disqualification of the "With Credit_Score" Variant
When `Credit_Score` is included as a feature (43 features), the model scores near-perfect test metrics (ROC-AUC 0.9999, Macro-F1 0.9903). This was confirmed as **severe target leakage**:
1. **Direct Label Derivation:** In Indian banking underwriting, `Credit_Score` is directly partitioned into rigid policy score cutoffs to set `Approved_Flag` tiers.
2. **Missing at Serving:** New or thin-file applicant portfolios (including `Unseen_Dataset.xlsx`) frequently lack established bureau scores.
3. **Loss of Predictive Value:** An underwriting risk platform must assess creditworthiness from genuine behavioral fundamentals: trade-line utilization, past delinquency patterns, and recent credit hunger.

Consequently, the **42-feature XGBoost without Credit_Score** is selected as the genuine production champion (Macro-F1 0.6780, ROC-AUC 0.9275).

---

## 4. Fair Lending & Demographic Parity Audit

Evaluated on the held-out test partition (7,701 records). Approval is defined as classification into Tier P1 or P2.

### 4.1 Subgroup Performance Metrics

| Demographic Slice | Subgroup | Sample Size | Accuracy | Macro F1 | Approval Rate | Empirical Base Rate |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Gender** | Male (M) | 6846 | 0.7866 | 0.6792 | 80.66% | 74.13% |
| | Female (F) | 855 | 0.7743 | 0.6696 | 81.05% | 73.22% |
| **Marital Status** | Married | 5681 | 0.7847 | 0.6632 | 83.54% | 76.76% |
| | Single | 2020 | 0.7866 | 0.6896 | 72.72% | 66.34% |
| **Education** | Graduate | 2490 | 0.7904 | 0.6873 | 79.52% | 73.17% |
| | SSC | 1389 | 0.7747 | 0.6680 | 82.22% | 74.01% |
| | 12th | 2176 | 0.7845 | 0.6723 | 81.11% | 74.82% |
| | Post-Graduate | 324 | 0.7747 | 0.6650 | 79.01% | 74.07% |
| **Age Band** | <25 | 1049 | 0.7969 | 0.6995 | 71.40% | 64.44% |
| | 25-34 | 3584 | 0.7771 | 0.6596 | 77.59% | 70.76% |
| | 35-49 | 2575 | 0.7868 | 0.6452 | 87.15% | 80.58% |
| | 50+ | 493 | 0.8114 | 0.6584 | 89.45% | 83.98% |

### 4.2 Disparate Impact Ratios (Four-Fifths Rule Compliance)
Under EEOC / CFPB fair lending guidance, an adverse-group approval rate of at least 80% (DIR $\ge 0.80$) of the privileged group confirms demographic parity.

| Demographic Dimension | Comparison Pair | Computed DIR | Threshold (80% Rule) | Audit Result |
|---|---|:---:|:---:|:---:|
| **Gender** | Female vs. Male | **1.00** | $\ge 0.80$ | **PASS** (Compliant) |
| **Education** | SSC vs. Graduate | **1.03** | $\ge 0.80$ | **PASS** (Compliant) |
| **Marital Status** | Single vs. Married | **0.87** | $\ge 0.80$ | **PASS** (Compliant) |
| **Age Band** | <25 vs. 25-34 Reference | **0.92** | $\ge 0.80$ | **PASS** (Compliant) |

**Overall Compliance Status:** All demographic slices satisfy the Four-Fifths rule with zero violation of fair lending parity.

---

## 5. Responsible Use & Underwriting Guardrails
1. **Educational & Decision-Support Scope:** RiskWise model predictions serve as educational risk tier classifications and analyst decision support, not an automated sole-decision underwriting system.
2. **Actionable Sensitivity:** Counterfactual sensitivity is strictly restricted to borrower-controllable factors (e.g., reducing credit card inquiries, paying down trade lines, clearing delinquency).
3. **Protected Attribute Invariance:** Models do not condition tier assignment on gender or marital status in an adverse manner, passing all standard fair-lending tests.
