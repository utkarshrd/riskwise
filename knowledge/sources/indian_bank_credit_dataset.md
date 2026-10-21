# Indian Bank Credit Dataset: Provenance and Methodology

> **Provenance Notice:** Team-authored educational summary based on the Indian bank loan default dataset collected from a private Indian bank and made available for academic research; not an official publication by the data originator.

## Dataset Provenance and Observation Window
The credit risk model used in RiskWise is trained on a proprietary Indian bank loan dataset containing records of retail borrowers from an Indian commercial bank. The dataset covers loan applicants with a multi-class repayment performance target across four risk grades: P1 (lowest risk) through P4 (highest risk / non-performing). Unlike the previously referenced Taiwan credit card benchmark, this dataset reflects contemporary Indian retail lending behaviour, income profiles, and loan product structures.

## Target Definition and Class Distribution
The multi-class target variable encodes four repayment performance categories:
- **P1**: Standard performing — borrower services EMI regularly with no delinquency.
- **P2**: Watch-list — occasional payment delays or irregularities; moderate delinquency risk.
- **P3**: Sub-standard — persistent payment irregularities; elevated probability of NPA classification.
- **P4**: Non-performing / default — account classified as NPA or write-off equivalent.

## Feature Architecture
Input features reflect the Indian retail lending context:
1. Loan attributes: principal amount, tenure, interest rate, EMI, loan-to-value ratio, product type (home, personal, vehicle, gold, etc.).
2. Bureau-derived signals: CIBIL score range, number of active loans, inquiry count, delinquency history flags.
3. Income and obligation profile: net monthly income, Fixed Obligation to Income Ratio (FOIR), employment type (salaried / self-employed), employer category.
4. Account behavior: days past due (DPD) history, repayment ratio over trailing periods.

## Model Architecture and Evaluation
The champion model is trained using XGBoost with SHAP explainability. Two variants were evaluated:
- **Without Credit_Score**: Feature set excludes bureau-derived CIBIL score fields to reflect scenarios where bureau data is unavailable (new-to-credit borrowers, thin-file applicants).
- **With Credit_Score**: Includes bureau scores, yielding near-perfect AUC (0.9999) which is expected because CIBIL score is a strong leading predictor of NPA classification and is effectively a summary statistic of repayment history. This variant is retained for demonstration but documented as bureau-dependent.

The **Without Credit_Score** variant is the primary champion for fair evaluation because it tests the model's predictive capability independent of the summary bureau score.

## Responsible Use Disclosures
This dataset is used strictly for academic research and educational demonstration purposes within the RiskWise engineering project. The model must not be used to make actual credit approval decisions for real Indian borrowers. Predicted risk grades (P1–P4) are research outputs, not CIBIL ratings, RBI-regulated credit assessments, or loan sanction decisions.
