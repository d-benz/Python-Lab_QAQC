import pandas as pd
import numpy as np


def base_name(sample):
    if not isinstance(sample, str):
        return None
    return sample.replace(" Meas", "").replace(" Cert", "").strip()


def compute_crm_recovery(df, metadata, low_tol=80.0, high_tol=120.0):
    """
    Compute CRM recovery and bias for each analyte in wide-format QC data.

    Status classifications per CRM run / analyte:
      - NotApplicable        : both values missing, or certified value < DL
      - NotEvaluated         : one value is missing
      - Below10xDL           : certified value < 10x DL (precision not meaningful)
      - Needs Investigation   : certified >= DL but measured < DL
      - OK                   : recovery within [low_tol, high_tol]
      - Fail                 : recovery outside tolerance

    Parameters
    ----------
    df : pd.DataFrame
        Wide-format QC table with 'Sample' and 'QC_Type' columns.
    metadata : dict
        Analyte metadata dict from load_metadata().
    low_tol : float
        Lower CRM recovery tolerance (%).
    high_tol : float
        Upper CRM recovery tolerance (%).

    Returns
    -------
    pd.DataFrame
        Per-analyte, per-CRM-run recovery results with status classifications.
    """
    df = df.copy()

    df["CRM_Base"] = df["Sample"].apply(base_name)

    df_crm = df[df["QC_Type"] == "CRM"]

    df_meas = df_crm[df_crm["Sample"].str.contains(" Meas", na=False)].copy()
    df_cert = df_crm[df_crm["Sample"].str.contains(" Cert", na=False)].copy()

    # Assign run index to prevent many-to-many merge when the same CRM
    # appears multiple times in the batch
    df_meas["CRM_Index"] = df_meas.groupby("CRM_Base").cumcount()
    df_cert["CRM_Index"] = df_cert.groupby("CRM_Base").cumcount()

    merged = pd.merge(
        df_meas,
        df_cert,
        on=["CRM_Base", "CRM_Index"],
        suffixes=("_Meas", "_Cert")
    )

    # Also carry the run order index through so qc_plots can plot by batch position
    merged["Run_Order"] = df_meas.reset_index(drop=True).index + 1

    results = []

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

        # Strip qualifier strings like "<0.005" or ">10000" -> NaN
        qual_pattern = r"^[<>]\s*\d+(\.\d+)?$"

        measured_clean = measured.astype(str).str.strip().replace(
            qual_pattern, np.nan, regex=True
        )
        certified_clean = certified.astype(str).str.strip().replace(
            qual_pattern, np.nan, regex=True
        )

        measured = pd.to_numeric(measured_clean, errors="coerce")
        certified = pd.to_numeric(certified_clean, errors="coerce")

        meas_blank = measured.isna()
        cert_blank = certified.isna()

        both_missing = meas_blank & cert_blank
        one_missing = (meas_blank | cert_blank) & ~both_missing

        recovery = pd.Series([None] * len(merged), dtype=object)
        bias = pd.Series([None] * len(merged), dtype=object)
        status = pd.Series([""] * len(merged), dtype=object)

        # 1) Both missing -> NotApplicable
        recovery[both_missing] = ""
        bias[both_missing] = ""
        status[both_missing] = "NotApplicable"

        # 2) One missing -> NotEvaluated
        recovery[one_missing] = ""
        bias[one_missing] = ""
        status[one_missing] = "NotEvaluated"

        # 3) Certified < DL -> NotApplicable
        cert_below_dl = (certified < dl) & ~(both_missing | one_missing)
        recovery[cert_below_dl] = ""
        bias[cert_below_dl] = ""
        status[cert_below_dl] = "NotApplicable"

        # 3b) Certified < 10x DL -> Below10xDL
        cert_below_10x = (
            (certified < (10 * dl))
            & ~(both_missing | one_missing | cert_below_dl)
        )
        recovery[cert_below_10x] = ""
        bias[cert_below_10x] = ""
        status[cert_below_10x] = "Below10xDL"

        # 4) Certified >= DL but measured < DL -> Needs Investigation
        needs_inv = (
            (certified >= dl)
            & (measured < dl)
            & ~(both_missing | one_missing | cert_below_dl | cert_below_10x)
        )
        recovery[needs_inv] = "BDL"
        bias[needs_inv] = "BDL"
        status[needs_inv] = "Needs Investigation"

        # 5) Valid numeric -> compute recovery and bias
        valid_mask = (
            ~(both_missing | one_missing | cert_below_dl | cert_below_10x | needs_inv)
            & measured.notna()
            & certified.notna()
        )

        recovery[valid_mask] = (measured[valid_mask] / certified[valid_mask]) * 100
        # Handle division by zero
        recovery[valid_mask & (certified[valid_mask] == 0)] = np.nan
        bias[valid_mask] = recovery[valid_mask] - 100

        recovery_num = pd.to_numeric(recovery, errors="coerce")
        numeric_mask = valid_mask & recovery_num.notna()

        status[numeric_mask & (recovery_num >= low_tol) & (recovery_num <= high_tol)] = "OK"
        status[numeric_mask & ((recovery_num < low_tol) | (recovery_num > high_tol))] = "Fail"

        results.append(pd.DataFrame({
            "CRM": merged["CRM_Base"],
            "CRM_Index": merged["CRM_Index"],
            "Analyte": analyte,
            "Unit": unit,
            "Measured": measured,
            "Certified": certified,
            "DL": dl,
            "Recovery": recovery,
            "Bias": bias,
            "CRM_Status": status,
        }))

    if results:
        return pd.concat(results, ignore_index=True)

    return pd.DataFrame()
