import pandas as pd

def classify_qc_row(sample_name):
    """
    Classify a QC row based on the sample name.
    """
    if not isinstance(sample_name, str) or sample_name.strip() == "":
        return "Other"

    name = sample_name.strip().upper()

    # Blank detection
    if "BLANK" in name or "BLK" in name:
        return "Blank"

    # Duplicate detection
    if " ORIG" in name or name.endswith("ORIG"):
        return "Duplicate_Orig"

    if " DUP" in name or name.endswith("DUP"):
        return "Duplicate_Dup"

    # CRM detection
    return "CRM"


def classify_qc_table(df):
    """
    Apply QC classification to the entire QC dataframe.
    Assumes there is a 'Sample' column.
    """
    df = df.copy()
    df["QC_Type"] = df["Sample"].apply(classify_qc_row)
    return df