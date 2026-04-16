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

    # Fallback
    return dl / 2.0


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
# MAIN BLANK QC MODULE
# ============================================================
def compute_blank_qc(df, metadata, tolerance_factor=3.0, bdl_rule="half"):
    """
    Evaluate method blanks in wide-format QC data.

    Status logic per analyte:
      - All values missing          -> NotEvaluated
      - ALL non-NaN values are BDL  -> OK  (ideal blank behaviour)
      - Any non-NaN value exceeds
        DL * tolerance_factor       -> Fail
      - Average >= DL               -> Needs Investigation
      - Average < DL                -> OK

    The previous logic flagged OK if *any* value was BDL, which could mask
    a genuine exceedance in another run of the same analyte. This version
    requires all evaluated values to be BDL before granting an OK on that
    basis alone.

    Parameters
    ----------
    df : pd.DataFrame
        Wide-format QC table with 'QC_Type' column.
    metadata : dict
        Analyte metadata dict from load_metadata().
    tolerance_factor : float
        Multiplier applied to DL to define the blank exceedance threshold.
    bdl_rule : str or numeric
        BDL substitution rule used for averaging below-detection values.

    Returns
    -------
    pd.DataFrame
        Per-analyte blank QC results with Average, StDev, and Blank_Status.
    """
    df = df.copy()

    df_blank = df[df["QC_Type"].str.contains("Blank", na=False)].reset_index(drop=True)

    if df_blank.empty:
        return pd.DataFrame()

    results = []

    for col_index, meta in metadata.items():

        analyte = meta["analyte"]
        unit = meta["unit"]
        dl = meta["dl"]

        col_name = f"{analyte}_{unit}".replace(" ", "").replace("/", "")

        if col_name not in df_blank.columns:
            continue

        raw = df_blank[col_name]

        # 1) All values missing -> NotEvaluated
        if raw.isna().all():
            results.append(pd.DataFrame({
                "Analyte": [analyte],
                "Unit": [unit],
                "DL": [dl],
                "Values": [list(raw)],
                "Average": [""],
                "StDev": [""],
                "Blank_Status": ["NotEvaluated"],
            }))
            continue

        # Convert to numeric using the substitution rule for averaging
        numeric = raw.apply(lambda x: to_numeric_with_bdl(x, dl, bdl_rule))
        valid = numeric.dropna()

        avg = valid.mean()
        stdev = valid.std(ddof=0) if len(valid) > 1 else 0.0

        # 2) Status logic
        # All non-NaN raw values are BDL -> ideal blank, OK
        non_null_raw = raw.dropna()
        all_bdl = non_null_raw.apply(is_bdl).all()

        if all_bdl:
            status = "OK"

        # Any substituted value exceeds tolerance threshold -> Fail
        elif (valid >= dl * tolerance_factor).any():
            status = "Fail"

        # Average is at or above DL but below threshold -> Needs Investigation
        elif avg >= dl:
            status = "Needs Investigation"

        # Average is below DL -> OK
        else:
            status = "OK"

        results.append(pd.DataFrame({
            "Analyte": [analyte],
            "Unit": [unit],
            "DL": [dl],
            "Values": [list(raw)],
            "Average": [avg],
            "StDev": [stdev],
            "Blank_Status": [status],
        }))

    if results:
        return pd.concat(results, ignore_index=True)

    return pd.DataFrame()
