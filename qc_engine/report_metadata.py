import os
import re
import pandas as pd

def extract_file_name(filepath):
    """
    Extract the full base file name without the extension.
    Example:
      A25-15568-Final2.xlsx → A25-15568-Final2
    """
    fname = os.path.basename(filepath)
    base = os.path.splitext(fname)[0]
    return base


def load_header_metadata(path, sheet="QC"):
    """
    Reads ONLY Column A of the QC sheet and extracts lines like:
      'Report Number: A25-15567'
      'Report Date: 2025/12/23'
    Returns a dict: {"Report Number": "...", "Report Date": "..."}
    """
    df = pd.read_excel(path, sheet_name=sheet, header=None)

    header = {}
    for val in df.iloc[:, 0].dropna().astype(str):
        if ":" in val:
            key, value = val.split(":", 1)
            header[key.strip().lower()] = value.strip()

    return header


def extract_meta_name(header_dict, meta_key="report number"):
    """
    Extracts the metadata name (e.g., report number) from the header dict.
    """
    return header_dict.get(meta_key.lower(), None)


def extract_report_date(header_dict, date_key="report date"):
    """
    Extracts the report date from the header dict.
    """
    return header_dict.get(date_key.lower(), None)


def extract_all_identifiers(filepath, metadata_dict, meta_key="report number", date_key="report date"):
    """
    Returns:
      file_name
      metadata_name
      report_date
      names_match (True/False)
    """
    file_name = extract_file_name(filepath)

    # NEW: load header metadata directly from QC sheet
    header = load_header_metadata(filepath)

    metadata_name = extract_meta_name(header, meta_key)
    report_date = extract_report_date(header, date_key)

    # Fallback if metadata missing
    if metadata_name is None:
        metadata_name = file_name

    names_match = (file_name == metadata_name)

    return file_name, metadata_name, report_date, names_match