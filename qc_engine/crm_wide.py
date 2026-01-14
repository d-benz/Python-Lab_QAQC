import pandas as pd
import numpy as np

def base_name(sample):
    if not isinstance(sample, str):
        return None
    return sample.replace(" Meas", "").replace(" Cert", "").strip()


def compute_crm_recovery(df, metadata, low_tol=80.0, high_tol=120.0):

    df = df.copy()

    # Extract base CRM name
    df["CRM_Base"] = df["Sample"].apply(base_name)

    # Keep only CRM rows
    df_crm = df[df["QC_Type"] == "CRM"]

    # Split into Meas and Cert
    df_meas = df_crm[df_crm["Sample"].str.contains(" Meas", na=False)].copy()
    df_cert = df_crm[df_crm["Sample"].str.contains(" Cert", na=False)].copy()

    # Assign run index to prevent many-to-many merge
    df_meas["CRM_Index"] = df_meas.groupby("CRM_Base").cumcount()
    df_cert["CRM_Index"] = df_cert.groupby("CRM_Base").cumcount()

    # Merge Meas and Cert rows by CRM_Base + CRM_Index
    merged = pd.merge(
        df_meas,
        df_cert,
        on=["CRM_Base", "CRM_Index"],
        suffixes=("_Meas", "_Cert")
    )

    results = []

    # Loop through analyte columns
    for col_index, meta in metadata.items():

        analyte = meta["analyte"]
        unit = meta["unit"]
        dl = meta["dl"]

        col_name = f"{analyte}_{unit}".replace(" ", "").replace("/", "")

        meas_col = col_name + "_Meas"
        cert_col = col_name + "_Cert"

        if meas_col not in merged.columns or cert_col not in merged.columns:
            continue

        measured = merged[meas_col]
        certified = merged[cert_col]

        # Clean "<X" and ">X" qualifiers → NaN
        qual_pattern = r"^[<>]\s*\d+(\.\d+)?$"

        measured_clean = measured.astype(str).str.strip().replace(qual_pattern, np.nan, regex=True)
        certified_clean = certified.astype(str).str.strip().replace(qual_pattern, np.nan, regex=True)

        # Convert remaining numeric strings to floats
        measured = pd.to_numeric(measured_clean, errors="coerce")
        certified = pd.to_numeric(certified_clean, errors="coerce")

        # Masks
        meas_blank = measured.isna()
        cert_blank = certified.isna()

        both_missing = meas_blank & cert_blank
        one_missing = (meas_blank | cert_blank) & ~both_missing

        # Initialize outputs
        recovery = pd.Series([None] * len(merged), dtype=object)
        bias = pd.Series([None] * len(merged), dtype=object)
        status = pd.Series([""] * len(merged), dtype=object)

        # 1) Both missing → NotApplicable
        recovery[both_missing] = ""
        bias[both_missing] = ""
        status[both_missing] = "NotApplicable"

        # 2) One missing → NotEvaluated
        recovery[one_missing] = ""
        bias[one_missing] = ""
        status[one_missing] = "NotEvaluated"

        # 3) Certified < DL → NotApplicable
        cert_below_dl = certified < dl
        mask_cert_below = cert_below_dl & ~(both_missing | one_missing)

        recovery[mask_cert_below] = ""
        bias[mask_cert_below] = ""
        status[mask_cert_below] = "NotApplicable"

        # 3b) Certified < 10× DL → Below10xDL
        cert_below_10x = (certified < (10 * dl)) & ~(both_missing | one_missing | mask_cert_below)
        mask_cert_below_10x = cert_below_10x

        recovery[mask_cert_below_10x] = ""
        bias[mask_cert_below_10x] = ""
        status[mask_cert_below_10x] = "Below10xDL"

        # 4) Certified ≥ DL AND Measured < DL → Needs Investigation
        mask_needs_inv = (
            (certified >= dl) &
            (measured < dl) &
            ~(both_missing | one_missing | mask_cert_below | mask_cert_below_10x)
        )

        recovery[mask_needs_inv] = "BDL"
        bias[mask_needs_inv] = "BDL"
        status[mask_needs_inv] = "Needs Investigation"

        # 5) Valid numeric → compute recovery and bias
        valid_mask = ~(both_missing | one_missing | mask_cert_below | mask_cert_below_10x | mask_needs_inv)
        valid_mask = valid_mask & measured.notna() & certified.notna()

        recovery[valid_mask] = (measured[valid_mask] / certified[valid_mask]) * 100
        bias[valid_mask] = recovery[valid_mask] - 100

        # Numeric comparison for OK/Fail
        recovery_num = pd.to_numeric(recovery, errors="coerce")
        numeric_mask = valid_mask & recovery_num.notna()

        status[numeric_mask & (recovery_num >= low_tol) & (recovery_num <= high_tol)] = "OK"
        status[numeric_mask & ((recovery_num < low_tol) | (recovery_num > high_tol))] = "Fail"


        # Build result table
        results.append(pd.DataFrame({
            "CRM": merged["CRM_Base"],
            "Analyte": analyte,
            "Unit": unit,
            "Measured": measured,
            "Certified": certified,
            "DL": dl,
            "Recovery": recovery,
            "Bias": bias,
            "CRM_Status": status
        }))

    if results:
        return pd.concat(results, ignore_index=True)

    return pd.DataFrame()