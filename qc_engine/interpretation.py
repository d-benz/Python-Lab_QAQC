import pandas as pd
import yaml
import os

# Load config
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)


# ------------------------------------------------------------
# BATCH SUMMARY
# ------------------------------------------------------------
def compute_batch_summary(df_qc, crm_results, dup_results):
    """
    Compute batch-level sample counts from df_qc.

    Returns
    -------
    dict with keys:
        total_samples      - CRM Meas runs + duplicate pairs + blank runs
        crm_samples        - number of CRM Meas runs
        crm_unique         - number of unique CRM base names
        duplicate_samples  - number of duplicate pairs (Orig only)
        blank_samples      - number of blank runs
    """
    if df_qc is None or "Sample" not in df_qc.columns or "QC_Type" not in df_qc.columns:
        return {
            "total_samples": 0,
            "crm_samples": 0,
            "crm_unique": 0,
            "duplicate_samples": 0,
            "blank_samples": 0,
        }

    df_local = df_qc.copy()
    sample_str = df_local["Sample"].astype(str)
    qctype_str = df_local["QC_Type"].astype(str)

    # CRM Meas runs
    crm_meas_mask = (qctype_str == "CRM") & sample_str.str.contains(" Meas", na=False)
    df_crm_meas = df_local.loc[crm_meas_mask].copy()
    crm_samples_count = df_crm_meas.shape[0]

    df_crm_meas["CRM_Base"] = (
        df_crm_meas["Sample"].str.replace(" Meas", "", regex=False).str.strip()
    )
    crm_unique_count = df_crm_meas["CRM_Base"].dropna().nunique()

    # Duplicate pairs
    dup_orig_mask = qctype_str == "Duplicate_Orig"
    duplicate_samples_count = df_local.loc[dup_orig_mask].shape[0]

    # Blank runs
    blank_mask = sample_str.str.upper().str.contains("BLK|BLANK", na=False)
    blank_samples_count = df_local.loc[blank_mask].shape[0]

    total_samples_count = crm_samples_count + duplicate_samples_count + blank_samples_count

    return {
        "total_samples": total_samples_count,
        "crm_samples": crm_samples_count,
        "crm_unique": crm_unique_count,
        "duplicate_samples": duplicate_samples_count,
        "blank_samples": blank_samples_count,
    }


# ------------------------------------------------------------
# MATRIX CONTEXT BLOCK
# ------------------------------------------------------------
def matrix_context(matrix_type):
    if matrix_type is None:
        matrix_type = "unknown"

    m = str(matrix_type).lower().strip()

    contexts = config['matrix_contexts']

    for key, text in contexts.items():
        if key in m or m in key:
            return text

    return contexts['default'].format(matrix_type=matrix_type)


# ------------------------------------------------------------
# METHOD CONTEXT BLOCK
# ------------------------------------------------------------
def method_context(method_code):
    m = str(method_code).upper().strip()

    contexts = config['method_contexts']

    for key, text in contexts.items():
        if key.upper() in m or m in key.upper():
            return text

    return contexts['default'].format(method_code=method_code)


# ------------------------------------------------------------
# QC METRIC SUMMARIES
# ------------------------------------------------------------
def summarize_crm(crm_results):
    empty = {
        "count": 0,
        "failures": 0,
        "failed": [],
        "crm_runs": 0,
        "crm_unique": 0,
        "fail_by_crm": {},
        "fail_by_analyte": {},
        "fail_grouped": {},
        "fail_list_grouped": [],
        "crm_fail_counts": {},
        "crm_fail_unique": 0,
        "crm_fail_pattern": "none",
    }

    if crm_results is None or crm_results.empty:
        return empty

    df = crm_results.copy()

    numeric_mask = pd.to_numeric(df["Recovery"], errors="coerce").notna()
    status_mask = df["CRM_Status"].isin(["OK", "Fail"])
    evaluable = df[numeric_mask & status_mask]

    if evaluable.empty:
        return empty

    failures = evaluable[evaluable["CRM_Status"] == "Fail"]

    # Use nunique() directly — no regex stripping needed
    crm_runs = df["CRM"].nunique()
    crm_unique = crm_runs  # each CRM base name is already the unique identifier

    fail_by_crm = failures.groupby("CRM")["Analyte"].apply(list).to_dict()
    fail_by_analyte = failures.groupby("Analyte")["CRM"].apply(list).to_dict()

    crm_fail_counts = {crm: len(analytes) for crm, analytes in fail_by_crm.items()}
    crm_fail_unique = len(crm_fail_counts)

    if crm_fail_unique == 0:
        crm_fail_pattern = "none"
    elif crm_fail_unique == 1:
        crm_fail_pattern = "single_crm"
    else:
        crm_fail_pattern = "multi_crm"

    fail_grouped = {}
    for analyte, group in failures.groupby("Analyte"):
        rec = pd.to_numeric(group["Recovery"], errors="coerce")
        fail_grouped[analyte] = {
            "count": len(group),
            "min": float(rec.min()),
            "max": float(rec.max()),
        }

    fail_list_grouped = []
    for analyte, info in fail_grouped.items():
        if info["count"] == 1:
            fail_list_grouped.append(f"{analyte}: {info['min']:.1f}%")
        else:
            fail_list_grouped.append(
                f"{analyte}: {info['min']:.1f}-{info['max']:.1f}% ({info['count']} runs)"
            )

    return {
        "count": len(evaluable),
        "failures": len(failures),
        "failed": [
            f"{row['Analyte']} ({row['Recovery']:.1f}%)"
            for _, row in failures.iterrows()
        ],
        "crm_runs": crm_runs,
        "crm_unique": crm_unique,
        "fail_by_crm": fail_by_crm,
        "fail_by_analyte": fail_by_analyte,
        "fail_grouped": fail_grouped,
        "fail_list_grouped": fail_list_grouped,
        "crm_fail_counts": crm_fail_counts,
        "crm_fail_unique": crm_fail_unique,
        "crm_fail_pattern": crm_fail_pattern,
    }


def summarize_duplicates(dup_results):
    if dup_results is None or dup_results.empty:
        return {"count": 0, "failures": 0, "failed": [], "skipped": 0}

    dup_numeric = dup_results[pd.to_numeric(dup_results["RPD"], errors="coerce").notna()]
    skipped = len(dup_results) - len(dup_numeric)

    if dup_numeric.empty:
        return {"count": 0, "failures": 0, "failed": [], "skipped": skipped}

    status_values = dup_numeric["Status"].astype(str).str.upper()
    fail_mask = status_values.isin(["FAIL", "FAIL_RPD"])
    failures = dup_numeric[fail_mask]

    # Report failures at the analyte level so the narrative aligns with the
    # aggregated duplicate plot status.
    if not failures.empty:
        failed_by_analyte = (
            failures.assign(
                RPD_num=pd.to_numeric(failures["RPD"], errors="coerce")
            )
            .groupby("Analyte", sort=False, as_index=False)["RPD_num"]
            .max()
        )
        failed_list = [
            f"{row['Analyte']} ({row['RPD_num']:.1f}% RPD)"
            for _, row in failed_by_analyte.iterrows()
        ]
    else:
        failed_list = []

    return {
        "count": len(dup_numeric),
        "failures": len(failed_list),
        "failed": failed_list,
        "skipped": skipped,
    }


def summarize_blanks(blank_results):
    if blank_results is None or blank_results.empty:
        return {"count": 0, "failures": 0, "failed": []}

    failures = blank_results[blank_results["Blank_Status"].str.upper() == "FAIL"]

    return {
        "count": len(blank_results),
        "failures": len(failures),
        "failed": [
            f"{row['Analyte']} ({row['Average']} > DL {row['DL']})"
            for _, row in failures.iterrows()
        ],
    }


# ------------------------------------------------------------
# INTERPRETATION BLOCKS
# ------------------------------------------------------------
def interpret_crm(metrics, crm_sample_count):
    if crm_sample_count == 0:
        return "The CRM component of this batch contains no CRM samples."

    if metrics["failures"] == 0:
        return (
            f"The CRM results show that all {crm_sample_count} CRM samples fall within "
            "expected recovery ranges for analytes above the evaluation threshold "
            "(typically >= 10x DL), indicating stable digestion performance and consistent "
            "instrument calibration."
        )

    grouped_lines = "\n".join(f"  - {line}" for line in metrics["fail_list_grouped"])

    if metrics["crm_fail_pattern"] == "single_crm":
        pattern_text = (
            "The CRM deviations originate from a single CRM material, a pattern that often "
            "reflects CRM-specific behaviour (e.g., matrix mismatch or certified value "
            "uncertainty) rather than a batch-wide analytical issue."
        )
    elif metrics["crm_fail_pattern"] == "multi_crm":
        pattern_text = (
            f"The CRM deviations occur across {metrics['crm_fail_unique']} different CRMs. "
            "When multiple CRMs show similar patterns, this may indicate method-level effects "
            "such as digestion inefficiency, calibration drift, or interference-related bias."
        )
    else:
        pattern_text = (
            "The CRM deviations do not follow a clear single-CRM or multi-CRM pattern. "
            "Review the affected analytes for known digestion limitations or "
            "interference-related behaviour."
        )

    return (
        f"The CRM results show {metrics['failures']} analyte-level deviations across "
        f"{crm_sample_count} CRM runs. Deviations by analyte:\n\n"
        f"{grouped_lines}\n\n"
        f"{pattern_text}\n\n"
        "When CRM deviations occur, review digestion conditions, calibration stability, and "
        "interference-control settings to confirm whether the method is performing within its "
        "expected analytical envelope."
    )


def interpret_duplicates(metrics, dup_sample_count, rpd_tol):
    if dup_sample_count == 0:
        return (
            "No duplicate samples were included in this batch, so analytical precision "
            "could not be evaluated."
        )

    if metrics["count"] == 0:
        return (
            "One duplicate sample was included, but all analytes were below 10x DL, "
            "so RPD-based precision could not be evaluated."
        )

    if metrics["failures"] == 0:
        return (
            f"The duplicate samples show that all analytes above 10x DL meet the "
            f"<= {rpd_tol}% RPD precision criterion, indicating stable analytical precision "
            "for this batch."
        )

    msg = (
        f"{metrics['failures']} analytes in the duplicate sample exceed the {rpd_tol}% RPD "
        f"threshold. Duplicate RPD values > {rpd_tol}% may reflect sample heterogeneity, "
        "low-grade variability, or analytical precision limits. Affected analytes include:\n"
        + "\n".join(f"  - {a}" for a in metrics["failed"])
        + "\n\nWhen duplicate failures occur, they typically indicate variability in sample "
        "preparation, subsampling, or analytical precision rather than systematic analytical bias."
    )

    if metrics.get("skipped", 0) > 0:
        msg += (
            f"\n\nAn additional {metrics['skipped']} analytes were below 10x DL or involved "
            "BDL values and were excluded from precision evaluation."
        )

    return msg


def interpret_blanks(metrics, blank_sample_count):
    if blank_sample_count == 0:
        return "The blank component of this batch contains no blank samples."

    if metrics["failures"] == 0:
        return (
            "The blank results show all analytes below detection limits, indicating no evidence "
            "of laboratory contamination or instrument carryover."
        )

    return (
        f"The blank results show {metrics['failures']} analytes exceeding blank thresholds, "
        "suggesting possible low-level contamination, memory effects, or instrument carryover. "
        "Affected analytes include:\n"
        + "\n".join(f"  - {a}" for a in metrics["failed"])
        + "\n\nWhen blank exceedances occur, review recent high-grade samples, rinse sequences, "
        "and contamination-control procedures. Consider whether affected analytes could influence "
        "the interpretation of low-grade samples in this batch."
    )


# ------------------------------------------------------------
# MAIN WRAPPER
# ------------------------------------------------------------
def generate_qc_interpretation(
    crm_results,
    dup_results,
    blank_results,
    df_qc,
    method_code,
    lab_name,
    file_name,
    metadata_name,
    report_date,
    matrix_type=None,
    crm_low_tol=None,
    crm_high_tol=None,
    duplicate_rpd_tol=None,
    blank_tol_factor=None,
    bdl_sub_rule=None,
):
    """
    Generate a full plain-text QC interpretation narrative.

    Parameters
    ----------
    crm_results : pd.DataFrame
        Output of compute_crm_recovery().
    dup_results : pd.DataFrame
        Output of compute_duplicate_rpd().
    blank_results : pd.DataFrame
        Output of compute_blank_qc().
    df_qc : pd.DataFrame
        Classified QC table (output of classify_qc_table()).
    method_code : str
        Digestion/analysis method code (e.g., "AR-ICPMS").
    lab_name : str
        Laboratory name.
    file_name : str
        Source file base name.
    metadata_name : str
        Report number or certificate identifier.
    report_date : str
        Report date string.
    matrix_type : str, optional
        Sample matrix type (e.g., "rock", "soil").
    crm_low_tol : float, optional
        Lower CRM recovery tolerance (%).
    crm_high_tol : float, optional
        Upper CRM recovery tolerance (%).
    duplicate_rpd_tol : float, optional
        Duplicate RPD tolerance (%).
    blank_tol_factor : float, optional
        Blank exceedance factor.
    bdl_sub_rule : str, optional
        BDL substitution rule applied.

    Returns
    -------
    str
        Multi-paragraph QC narrative suitable for copying into a report.
    """
    text = []

    # Header
    text.append(f"QC Summary — {file_name} (Certificate: {metadata_name}, Date: {report_date})")
    text.append(f"Laboratory: {lab_name}")
    text.append("")

    # Batch summary
    batch = compute_batch_summary(df_qc, crm_results, dup_results)

    text.append(
        f"This batch includes {batch['total_samples']} total QC samples, consisting of "
        f"{batch['crm_samples']} CRM runs across {batch['crm_unique']} unique CRM materials, "
        f"{batch['duplicate_samples']} duplicate pairs, and {batch['blank_samples']} method blanks."
    )
    text.append("")

    # Method context
    text.append(
        "Understanding the digestion chemistry and detection technique is important for "
        "interpreting CRM recoveries, duplicate precision, and blank performance."
    )
    text.append("")
    text.append(method_context(method_code))
    text.append("")

    # CRM section
    text.append("CRM Behaviour:")
    text.append(
        "CRM performance provides insight into digestion consistency, calibration stability, "
        "interference behaviour, and whether the method is operating within its expected "
        "analytical envelope."
    )
    text.append("")
    text.append(f"CRM tolerance applied: {crm_low_tol:.0f}-{crm_high_tol:.0f}% recovery.")
    text.append("  Recovery (%) = (Measured / Certified) x 100")
    text.append("  Bias (%)     = ((Measured - Certified) / Certified) x 100")
    text.append("")

    crm_metrics = summarize_crm(crm_results)
    text.append(interpret_crm(crm_metrics, batch["crm_samples"]))
    text.append("")

    # Duplicate section
    text.append("Duplicate Behaviour:")
    text.append(
        "Duplicate samples evaluate analytical precision. For analytes present at >= 10x the "
        "detection limit, precision is typically 5-10% RSD. Elements near the detection limit, "
        "or sensitive to adsorption, partial digestion, or matrix effects, commonly show "
        "higher RPD values."
    )
    text.append("")
    text.append(f"Duplicate tolerance applied: <= {duplicate_rpd_tol:.0f}% RPD.")
    text.append(
        "  RPD (%) = |Sample1 - Sample2| / ((Sample1 + Sample2) / 2) x 100"
    )
    text.append("")

    dup_metrics = summarize_duplicates(dup_results)
    text.append(interpret_duplicates(dup_metrics, batch["duplicate_samples"], duplicate_rpd_tol))
    text.append("")
    text.append(matrix_context(matrix_type))
    text.append("")

    # Blank section
    text.append("Blank Behaviour:")
    text.append(
        "Blank samples help identify contamination, memory effects, and instrument carryover. "
        "Exceedances should be considered when interpreting low-grade sample results."
    )
    text.append("")
    text.append(f"Blank tolerance applied: values > {blank_tol_factor:.1f}x DL flagged.")
    text.append(f"BDL substitution rule applied: {bdl_sub_rule}.")
    text.append("  Blank mean = sum(blank values) / n")
    text.append("  Blank SD   = sqrt( sum((x - mean)^2) / (n - 1) )")
    text.append("")

    blk_metrics = summarize_blanks(blank_results)
    text.append(interpret_blanks(blk_metrics, batch["blank_samples"]))
    text.append("")

    # Disclaimer
    text.append(
        "Note: QC results reflect internal laboratory quality-control performance for this "
        "batch. They highlight patterns that may warrant further review but should be "
        "interpreted alongside laboratory documentation and project context. This output is "
        "descriptive and educational — professional judgement remains essential."
    )
    text.append("")

    # Status definitions
    text.append(
        "Status definitions:\n"
        "  OK                  - Result falls within the defined tolerance.\n"
        "  Fail                - Result exceeds the defined tolerance.\n"
        "  Fail_RPD            - Duplicate RPD exceeds the precision tolerance.\n"
        "  BDL_Substitution    - One value is BDL; substitution was applied for RPD calculation.\n"
        "  BothBDL             - Both values are BDL; evaluation is not meaningful.\n"
        "  Below10xDL          - Values are below 10x DL; evaluation is not meaningful.\n"
        "  Needs Investigation - Borderline condition requiring further review.\n"
        "  NotApplicable       - Certified value or both measurements are below DL.\n"
        "  NotEvaluated        - Required data are missing."
    )
    text.append("")

    return "\n".join(text)
