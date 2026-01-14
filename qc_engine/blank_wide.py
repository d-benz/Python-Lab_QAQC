import pandas as pd
import numpy as np

# ============================================================
# BDL SUBSTITUTION RULE (easy to change)
# ============================================================
def bdl_substitution(dl, rule):
    if isinstance(rule, (int, float)):
        return float(rule)

    rule = str(rule).lower()

    if rule == "half":
        return dl / 2.0
    if rule == "sqrt2":
        return dl / np.sqrt(2)
    if rule == "zero":
        return 0.0
    if rule == "dl":
        return dl

    # fallback
    return dl / 2.0



def is_bdl(x):
    """Detect values like '< 0.2'."""
    return isinstance(x, str) and x.strip().startswith("<")


def to_numeric_with_bdl(x, dl, rule):
    """
    Convert values to numeric for calculations.
    - If BDL string → use substitution rule
    - If numeric → float
    - If blank → NaN
    """
    if pd.isna(x):
        return np.nan
    if is_bdl(x):
        return bdl_substitution(dl, rule)
    try:
        return float(x)
    except:
        return np.nan


# ============================================================
# MAIN BLANK QC MODULE
# ============================================================
def compute_blank_qc(df, metadata, tolerance_factor=3.0, bdl_rule="half"):
    """
    Evaluate method blanks in wide-format QC data.

    Updated logic:
      - If all blank values are blank → NotEvaluated
      - If ANY measured value < DL → OK   (BDL blanks are ideal)
      - Else:
            avg = mean(substituted numeric values)
            stdev = stdev(substituted numeric values)
            If avg < DL → OK
            If DL ≤ avg < DL * tolerance_factor → Needs Investigation
            If avg ≥ DL * tolerance_factor → Fail
    """

    df = df.copy()

    # Select blank rows and reset index
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

        # Convert to numeric with substitution for averaging
        numeric = raw.apply(lambda x: to_numeric_with_bdl(x, dl, bdl_rule))

        # 1) All blank → NotEvaluated
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

        # Drop NaNs for calculations
        valid = numeric.dropna()
        avg = valid.mean()
        stdev = valid.std(ddof=0)

        # 2) Status logic
        # --------------------------------------------------------
        # If ANY raw value is BDL → OK
        # --------------------------------------------------------
        if any(is_bdl(x) for x in raw):
            status = "OK"

        else:
            # No BDL values → evaluate using average
            if avg < dl:
                status = "OK"
            elif avg < dl * tolerance_factor:
                status = "Needs Investigation"
            else:
                status = "Fail"



        results.append(pd.DataFrame({
            "Analyte": [analyte],
            "Unit": [unit],
            "DL": [dl],
            "Values": [list(raw)],
            "Average": [avg],
            "StDev": [stdev],
            "Blank_Status": [status],
        }))

    return pd.concat(results, ignore_index=True)