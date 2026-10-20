# Default of Credit Card Clients Dataset: Provenance and Methodology

> **Provenance Notice:** Team-authored educational summary based on Yeh & Lien (Expert Systems with Applications, 2009); not an official publication by the authors or UCI repository.

## Dataset Provenance and Observation Window
The benchmark dataset used in RiskWise is the UCI Machine Learning Repository "Default of Credit Card Clients" dataset, published by I-Cheng Yeh and Che-hui Lien (2009). The dataset records 30,000 credit card accounts from an issuer in Taiwan between April 2005 and September 2005.

## Target Definition and Class Distribution
The binary target variable (`default_payment_next_month`) records whether a client defaulted on payment in October 2005 (1 = default, 0 = non-default). The dataset has an empirical default prevalence of 22.12% (6,636 defaults out of 30,000 records).

## Feature Architecture
The 23 input features include:
1. Demographic attributes: Credit limit (LIMIT_BAL), sex, education level, marital status, and age.
2. Historical payment tracking: Monthly repayment status (PAY_0 through PAY_6, April to September 2005) categorized as -1 (paid duly), 0 (revolving credit use), and 1 to 8 (payment delay in months).
3. Statement amounts: Monthly bill statements (BILL_AMT1 through BILL_AMT6).
4. Repayment amounts: Monthly payment amounts credited (PAY_AMT1 through PAY_AMT6).

## Proxy Limitations and Responsible Use Disclosures
This benchmark reflects historical consumer borrowing behavior in Taiwan from 2005. It is strictly an educational ML benchmark and proxy data source. The model trained on this dataset must never be interpreted as calculating an authentic CIBIL score, Indian credit rating, or real-world calibrated probability of default for contemporary Indian borrowers.
