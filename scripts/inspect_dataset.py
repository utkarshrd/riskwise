import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

DATASET_DIR = Path("dataset")
ext_path = DATASET_DIR / "External_Cibil_Dataset.xlsx"
int_path = DATASET_DIR / "Internal_Bank_Dataset.xlsx"
unseen_path = DATASET_DIR / "Unseen_Dataset.xlsx"

print("--- Reading External Cibil Dataset ---")
xl_ext = pd.ExcelFile(ext_path)
print("External Sheets:", xl_ext.sheet_names)
df_ext = pd.read_excel(ext_path, sheet_name=xl_ext.sheet_names[0])
print(f"External Shape: {df_ext.shape}")

print("\n--- Reading Internal Bank Dataset ---")
xl_int = pd.ExcelFile(int_path)
print("Internal Sheets:", xl_int.sheet_names)
df_int = pd.read_excel(int_path, sheet_name=xl_int.sheet_names[0])
print(f"Internal Shape: {df_int.shape}")

print("\n--- Reading Unseen Dataset ---")
xl_unseen = pd.ExcelFile(unseen_path)
print("Unseen Sheets:", xl_unseen.sheet_names)
df_unseen = pd.read_excel(unseen_path, sheet_name=xl_unseen.sheet_names[0])
print(f"Unseen Shape: {df_unseen.shape}")

# Check PROSPECTID
print("\n--- PROSPECTID Analysis ---")
print("PROSPECTID in ext:", "PROSPECTID" in df_ext.columns)
print("PROSPECTID in int:", "PROSPECTID" in df_int.columns)
print("PROSPECTID in unseen:", "PROSPECTID" in df_unseen.columns)
print("Ext PROSPECTID unique:", df_ext["PROSPECTID"].nunique(), "Total rows:", len(df_ext))
print("Int PROSPECTID unique:", df_int["PROSPECTID"].nunique(), "Total rows:", len(df_int))

common_ids = set(df_ext["PROSPECTID"]).intersection(set(df_int["PROSPECTID"]))
print("Common PROSPECTIDs:", len(common_ids))
print("Only in Ext:", len(set(df_ext["PROSPECTID"]) - common_ids))
print("Only in Int:", len(set(df_int["PROSPECTID"]) - common_ids))

# Check overlapping columns
common_cols = set(df_ext.columns).intersection(set(df_int.columns))
print("\nOverlapping columns between ext and int:", common_cols)

# Check Target
print("\n--- Target Approved_Flag Analysis ---")
if "Approved_Flag" in df_ext.columns:
    print("Approved_Flag in Ext:")
    print(df_ext["Approved_Flag"].value_counts(dropna=False))
if "Approved_Flag" in df_int.columns:
    print("Approved_Flag in Int:")
    print(df_int["Approved_Flag"].value_counts(dropna=False))
if "Approved_Flag" in df_unseen.columns:
    print("Approved_Flag in Unseen:")
    print(df_unseen["Approved_Flag"].value_counts(dropna=False))

# Check Credit_Score
if "Credit_Score" in df_ext.columns:
    print("\nCredit_Score in Ext:")
    print(df_ext["Credit_Score"].describe())
    print("Sentinel -99999 count in Credit_Score:", (df_ext["Credit_Score"] == -99999).sum())
if "Credit_Score" in df_int.columns:
    print("\nCredit_Score in Int:")
    print(df_int["Credit_Score"].describe())

# Sentinel -99999 search across all columns
print("\n--- Sentinel -99999 Search ---")
ext_sentinels = {}
for col in df_ext.columns:
    if df_ext[col].dtype in [np.int64, np.float64, int, float]:
        cnt = (df_ext[col] == -99999).sum()
        if cnt > 0:
            ext_sentinels[col] = cnt
print("External columns with -99999:", len(ext_sentinels))
for k, v in list(ext_sentinels.items())[:10]:
    print(f"  {k}: {v} rows ({v/len(df_ext)*100:.2f}%)")

int_sentinels = {}
for col in df_int.columns:
    if df_int[col].dtype in [np.int64, np.float64, int, float]:
        cnt = (df_int[col] == -99999).sum()
        if cnt > 0:
            int_sentinels[col] = cnt
print("Internal columns with -99999:", len(int_sentinels))
for k, v in list(int_sentinels.items())[:10]:
    print(f"  {k}: {v} rows ({v/len(df_int)*100:.2f}%)")

unseen_sentinels = {}
for col in df_unseen.columns:
    if df_unseen[col].dtype in [np.int64, np.float64, int, float]:
        cnt = (df_unseen[col] == -99999).sum()
        if cnt > 0:
            unseen_sentinels[col] = cnt
print("Unseen columns with -99999:", len(unseen_sentinels))

# Compare columns of unseen vs merged
merged_cols = set(df_ext.columns).union(set(df_int.columns))
unseen_cols = set(df_unseen.columns)
print("\n--- Unseen Dataset Column Comparison ---")
print("Unseen cols count:", len(unseen_cols))
print("Unseen cols in merged:", len(unseen_cols.intersection(merged_cols)))
print("Unseen cols NOT in merged:", unseen_cols - merged_cols)
missing_in_unseen = merged_cols - unseen_cols
print("Merged cols NOT in unseen count:", len(missing_in_unseen))
