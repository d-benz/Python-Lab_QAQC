import pandas as pd
import numpy as np
import re

# ============================================================
# BDL SUBSTITUTION RULE
# ============================================================
def bdl_substitution(dl):
    return dl / 2.0


def base_name(sample):
    if not isinstance(sample, str):
        return None
    return sample.replace(" Orig", "").replace(" Dup", "").strip()


def is_bdl(x):
    return isinstance(x, str) and x.strip().startswith("<")


def to_numeric_with_bdl(x, dl):
    if pd.isna(x):
        return np.nan
    if is_bdl(x):
        return bdl_substitution(dl)
    try:
        return float(x)
    except:
        return np.nan


# ============================================================
# MAIN FUNCTION
# ============================================================
def compute_duplicate_rpd(df, metadata, rpd_tolerance=30.0):
    """
    Compute duplicate RPD with full QC logic including:
      - BDL handling
      - Missing values
      - 10× DL rule for precision evaluation
    """

    df = df.copy()
    df["DUP_Base"] = df["Sample"].apply(base_name)

    df_dup = df[df["QC_Type"].str.contains("Duplicate", na=False)]
    df_orig = df_dup[df_dup["QC_Type"] == "Duplicate_Orig"]
    df_dupe = df_dup[df_dup["QC_Type"] == "Duplicate_Dup"]

    merged = pd.merge(
        df_orig,
        df_dupe,
        on="DUP_Base",
        suffixes=("_Orig", "_Dup")
    )

    results = []

    for col_index, meta in metadata.items():

        analyte = meta["analyte"]
        unit = meta["unit"]
        dl = meta["dl"]

        col_name = f"{analyte}_{unit}".replace(" ", "").replace("/", "")

        orig_col = col_name + "_Orig"
        dup_col = col_name + "_Dup"

        if orig_col not in merged.columns or dup_col not in merged.columns:
            continue

        orig_raw = merged[orig_col]
        dup_raw = merged[dup_col]

        # Identify missing values
        orig_blank = orig_raw.isna()
        dup_blank = dup_raw.isna()
        blank_mask = orig_blank | dup_blank

        # Identify BDL
        orig_bdl = orig_raw.apply(is_bdl)
        dup_bdl = dup_raw.apply(is_bdl)

        # Numeric versions
        orig_num = orig_raw.apply(lambda x: to_numeric_with_bdl(x, dl))
        dup_num = dup_raw.apply(lambda x: to_numeric_with_bdl(x, dl))

        # 10× DL rule
        above_10x = (orig_num > 10 * dl) & (dup_num > 10 * dl)

        # Initialize outputs
        rpd = pd.Series([None] * len(merged), dtype=object)
        status = pd.Series([""] * len(merged), dtype=object)

        # 1) Missing values
        rpd[blank_mask] = ""
        status[blank_mask] = "NotEvaluated"

        # 2) Both BDL
        both_bdl = orig_bdl & dup_bdl & ~blank_mask
        rpd[both_bdl] = ""
        status[both_bdl] = "BothBDL"

        # 3) One BDL, one detected
        bdl_mismatch = ((orig_bdl & ~dup_bdl) | (dup_bdl & ~orig_bdl)) & ~blank_mask
        rpd[bdl_mismatch] = (
            (orig_num[bdl_mismatch] - dup_num[bdl_mismatch]).abs()
            / ((orig_num[bdl_mismatch] + dup_num[bdl_mismatch]) / 2)
            * 100
        )
        status[bdl_mismatch] = "BDL_Substitution"

        # 4) Both detected but <10× DL → precision not meaningful
        low_grade = (~orig_bdl) & (~dup_bdl) & ~blank_mask & ~above_10x
        rpd[low_grade] = ""
        status[low_grade] = "Below10xDL"

        # 5) Valid precision evaluation (both >10× DL)
        valid = above_10x & ~blank_mask & ~orig_bdl & ~dup_bdl
        rpd[valid] = (
            (orig_num[valid] - dup_num[valid]).abs()
            / ((orig_num[valid] + dup_num[valid]) / 2)
            * 100
        )

        # Compare numeric RPD to tolerance
        rpd_num = pd.to_numeric(rpd, errors="coerce")
        numeric_mask = valid & rpd_num.notna()

        status[numeric_mask & (rpd_num <= rpd_tolerance)] = "OK"
        status[numeric_mask & (rpd_num > rpd_tolerance)] = "Fail_RPD"

        results.append(pd.DataFrame({
            "Sample": merged["DUP_Base"],
            "Analyte": analyte,
            "Unit": unit,
            "Orig": orig_raw,
            "Dup": dup_raw,
            "Orig_num": orig_num,
            "Dup_num": dup_num,
            "DL": dl,
            "Above10xDL": above_10x,
            "RPD": rpd,
            "Status": status,
        }))

    if results:
        return pd.concat(results, ignore_index=True)

    return pd.DataFrame()