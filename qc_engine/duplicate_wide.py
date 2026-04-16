import pandas as pd
import numpy as np


# ============================================================
# BDL SUBSTITUTION RULE
# ============================================================
def bdl_substitution(dl, rule):
    """
    Apply the user-defined BDL substitution rule to a detection limit value.

    Parameters
    ----------
    dl : float
        Detection limit for the analyte.
    rule : str or numeric
        Substitution rule. Accepted string values: "half", "sqrt2", "zero", "dl".
        A numeric value is used directly as the substituted constant.

    Returns
    -------
    float
        Substituted numeric value.
    """
    if isinstance(rule, (int, float)):
        return float(rule)

    rule = str(rule).lower().strip()

    if rule == "half":
        return dl / 2.0
    if rule == "sqrt2":
        return dl / np.sqrt(2)
    if rule == "zero":
        return 0.0
    if rule == "dl":
        return dl

    # Fallback — matches blank_wide.py default behaviour
    return dl / 2.0


def base_name(sample):
    if not isinstance(sample, str):
        return None
    return sample.replace(" Orig", "").replace(" Dup", "").strip()


def is_bdl(x):
    """Detect BDL strings such as '< 0.005' or '<0.2'."""
    return isinstance(x, str) and x.strip().startswith("<")


def to_numeric_with_bdl(x, dl, rule):
    """
    Convert a raw cell value to a float for calculation.

    - BDL string  -> apply bdl_substitution(dl, rule)
    - Numeric     -> float
    - NaN / blank -> np.nan
    """
    if pd.isna(x):
        return np.nan
    if is_bdl(x):
        return bdl_substitution(dl, rule)
    try:
        return float(x)
    except (ValueError, TypeError):
        return np.nan


# ============================================================
# MAIN FUNCTION
# ============================================================
def compute_duplicate_rpd(
    df,
    metadata,
    rpd_tolerance=30.0,
    bdl_rule="half",
    bdl_substitution_rpd_tolerance=None,
):
    """
    Compute duplicate RPD with full QC logic including:
      - BDL handling using the user-defined bdl_rule
      - Missing values
      - 10x DL rule for precision evaluation
      - Separate tolerance for one-value BDL substitution cases

    Parameters
    ----------
    df : pd.DataFrame
        Wide-format QC table with 'Sample' and 'QC_Type' columns.
    metadata : dict
        Analyte metadata dict from load_metadata().
    rpd_tolerance : float
        RPD threshold above which duplicates are flagged as Fail_RPD.
    bdl_rule : str or numeric
        BDL substitution rule passed through to bdl_substitution().
    bdl_substitution_rpd_tolerance : float or None
        Optional, separate RPD threshold for cases where one value is BDL and
        substitution is applied. If None, the standard rpd_tolerance is used.

    Returns
    -------
    pd.DataFrame
        Per-analyte duplicate RPD results with status classifications.
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

        # Numeric versions — bdl_rule is now correctly forwarded
        orig_num = orig_raw.apply(lambda x: to_numeric_with_bdl(x, dl, bdl_rule))
        dup_num = dup_raw.apply(lambda x: to_numeric_with_bdl(x, dl, bdl_rule))

        # 10x DL rule
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

        # 3) One BDL, one detected — compute RPD using substituted values
        bdl_mismatch = ((orig_bdl & ~dup_bdl) | (dup_bdl & ~orig_bdl)) & ~blank_mask
        denominator = (orig_num[bdl_mismatch] + dup_num[bdl_mismatch]) / 2
        rpd[bdl_mismatch] = (
            (orig_num[bdl_mismatch] - dup_num[bdl_mismatch]).abs()
            / denominator
            * 100
        )
        # Handle zero denominator
        rpd[bdl_mismatch & (denominator == 0)] = np.nan

        bdl_tol = (
            rpd_tolerance
            if bdl_substitution_rpd_tolerance is None
            else bdl_substitution_rpd_tolerance
        )
        bdl_valid = bdl_mismatch & rpd.notna()
        status[bdl_mismatch & ~bdl_valid] = "NotEvaluated"
        rpd_numeric = pd.to_numeric(rpd, errors='coerce')
        status[bdl_valid & (rpd_numeric <= bdl_tol)] = "BDL_Substitution"
        status[bdl_valid & (rpd_numeric > bdl_tol)] = "Fail_RPD"

        # 4) Both detected but < 10x DL -> precision not meaningful
        low_grade = (~orig_bdl) & (~dup_bdl) & ~blank_mask & ~above_10x
        rpd[low_grade] = ""
        status[low_grade] = "Below10xDL"

        # 5) Valid precision evaluation (both > 10x DL)
        valid = above_10x & ~blank_mask & ~orig_bdl & ~dup_bdl
        denominator_valid = (orig_num[valid] + dup_num[valid]) / 2
        rpd[valid] = (
            (orig_num[valid] - dup_num[valid]).abs()
            / denominator_valid
            * 100
        )
        # Handle zero denominator
        rpd[valid & (denominator_valid == 0)] = np.nan

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
