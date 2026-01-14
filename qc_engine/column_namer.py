def rename_analyte_columns(df_qc, metadata):
    """
    Rename analyte columns using metadata:
    e.g., column 1 → 'Ti_ppm', column 2 → 'Fe_pct', etc.

    Assumes:
      - df_qc comes from load_qc_table (col 0 = sample name, 1..N = analytes)
      - metadata is a dict mapping column index → {'analyte', 'unit', ...}
    """
    df = df_qc.copy()

    # Rename column 0 (Excel column A) to 'Sample'
    new_cols = {0: "Sample"}

    # If metadata is not a dict, bail out early
    if not isinstance(metadata, dict):
        raise TypeError(
            f"metadata must be a dict, got {type(metadata)} instead. "
            "Check that load_metadata() is returning the parsed dictionary."
        )

    for col_index, meta in metadata.items():
        # Skip anything that doesn't look like an analyte metadata dict
        if not isinstance(meta, dict):
            continue
        if "analyte" not in meta or "unit" not in meta:
            continue

        analyte = str(meta["analyte"])
        unit = str(meta["unit"])

        clean_name = f"{analyte}_{unit}"
        clean_name = clean_name.replace(" ", "").replace("/", "")

        new_cols[col_index] = clean_name

    df = df.rename(columns=new_cols)

    return df