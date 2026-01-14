import pandas as pd


def load_metadata_block(path, sheet):
    """
    Load the first 6 rows of the QC sheet, which contain:
    Row 1: Report Number
    Row 2: Report Date
    Row 3: Analyte Symbol
    Row 4: Unit Symbol
    Row 5: Detection Limit
    Row 6: Analysis Method
    """
    meta_raw = pd.read_excel(path, sheet_name=sheet, nrows=6, header=None)
    return meta_raw


def extract_analyte_metadata(meta_raw):
    """
    Extract analyte metadata from the metadata block.

    Rows (0-based indices):
        2: Analyte Symbol
        3: Unit Symbol
        4: Detection Limit
        5: Analysis Method

    Columns 1..N (B→end) correspond to analytes.
    """

    analytes = meta_raw.iloc[2, 1:].tolist()
    units = meta_raw.iloc[3, 1:].tolist()
    dls = meta_raw.iloc[4, 1:].tolist()
    methods = meta_raw.iloc[5, 1:].tolist()

    metadata = {}

    for i, analyte in enumerate(analytes):
        if pd.isna(analyte):
            continue

        col_index = i + 1  # because column 0 is QC sample name

        metadata[col_index] = {
            "analyte": analyte,
            "unit": units[i],
            "dl": dls[i],
            "method": methods[i],
        }

    return metadata


def load_qc_block(path, sheet="QC"):
    """
    Load the QC data block starting at row 7 (skip first 6 rows).
    No header row in the QC block, so header=None.
    """
    df_qc = pd.read_excel(
        path,
        sheet_name=sheet,
        skiprows=6,
        header=None,
    )
    return df_qc


def load_metadata(path, sheet="QC"):
    """
    Convenience wrapper: return parsed analyte metadata dict.
    """
    meta_raw = load_metadata_block(path, sheet)
    metadata = extract_analyte_metadata(meta_raw)
    return metadata


def load_qc_table(path, sheet="QC"):
    """
    Convenience wrapper: load QC block (rows 7+).
    """
    return load_qc_block(path, sheet)