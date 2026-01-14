import pandas as pd

# ------------------------------------------------------------
# BATCH SUMMARY
# ------------------------------------------------------------

def compute_batch_summary(df_qc, crm_results, dup_results):
    """
    Compute batch-level sample counts from df_qc, with:

      - total_samples      = CRM Meas runs + duplicate pairs + blank runs
      - crm_samples        = number of CRM Meas runs
      - crm_unique         = number of unique CRM Meas base names
      - duplicate_samples  = number of duplicate pairs (Orig/Dup)
      - blank_samples      = number of blank runs
    """

    if df_qc is None or "Sample" not in df_qc.columns or "QC_Type" not in df_qc.columns:
        return {
            "total_samples": 0,
            "crm_samples": 0,
            "crm_unique": 0,
            "duplicate_samples": 0,
            "blank_samples": 0,
        }

    df_qc_local = df_qc.copy()
    sample_str = df_qc_local["Sample"].astype(str)
    qctype_str = df_qc_local["QC_Type"].astype(str)

    # -----------------------------
    # CRM Meas runs and unique CRMs
    # -----------------------------
    crm_meas_mask = (qctype_str == "CRM") & sample_str.str.contains(" Meas", na=False)
    df_crm_meas = df_qc_local.loc[crm_meas_mask].copy()

    # Number of CRM Meas runs (e.g., 13)
    crm_samples_count = df_crm_meas.shape[0]

    # Base CRM name: strip " Meas"
    df_crm_meas["CRM_Base"] = df_crm_meas["Sample"].str.replace(" Meas", "", regex=False).str.strip()

    # Number of unique CRMs (e.g., 8)
    crm_unique_count = df_crm_meas["CRM_Base"].dropna().nunique()

    # -----------------------------
    # Duplicate samples = pairs
    # Assume QC_Type has "Duplicate_Orig" and "Duplicate_Dup"
    # -----------------------------
    dup_orig_mask = qctype_str == "Duplicate_Orig"
    df_dup_orig = df_qc_local.loc[dup_orig_mask].copy()

    # Each Orig corresponds to one Dup → number of duplicate pairs
    duplicate_samples_count = df_dup_orig.shape[0]

    # -----------------------------
    # Blank runs
    # -----------------------------
    blank_mask = sample_str.str.upper().str.contains("BLK|BLANK")
    df_blanks = df_qc_local.loc[blank_mask].copy()
    blank_samples_count = df_blanks.shape[0]

    # -----------------------------
    # Total samples (QC runs)
    # -----------------------------
    total_samples_count = crm_samples_count + duplicate_samples_count + blank_samples_count

    return {
        "total_samples": total_samples_count,
        "crm_samples": crm_samples_count,          # e.g., 13 CRM Meas runs
        "crm_unique": crm_unique_count,           # e.g., 8 distinct CRM materials
        "duplicate_samples": duplicate_samples_count,  # e.g., 1 duplicate pair
        "blank_samples": blank_samples_count,     # e.g., 2 blank runs
    }


# ------------------------------------------------------------
# MATRIX CONTEXT BLOCK
# ------------------------------------------------------------

def matrix_context(matrix_type):
    if matrix_type is None:
        matrix_type = "unknown"

    m = str(matrix_type).lower().strip()

    # -------------------------
    # Hard rock
    # -------------------------
    if m in ["rock", "rocks", "hardrock", "hard rock", "core", "grab", "float", "chip"]:
        return (
            "Duplicate precision in hard‑rock material is typically reliable, and elevated RPD values "
            "may indicate subsampling variability or analytical precision limits."
        )

    # -------------------------
    # Soil
    # -------------------------
    if m in ["soil", "soils", "soil sample", "b horizon", "c horizon", "ah horizon"]:
        return (
            "These samples are soils, which commonly contain variable clay content, organics, and "
            "oxide coatings. Moderate variability in duplicate precision is not unusual, particularly "
            "for elements sensitive to adsorption or partial digestion."
        )

    # -------------------------
    # Organic-rich soils
    # -------------------------
    if m in ["organic soil", "peat", "humus", "ah", "o/a", "o horizon"]:
        return (
            "Organic‑rich soils often show elevated duplicate variability due to heterogeneous organic "
            "content and variable digestion efficiency."
        )

    # -------------------------
    # Till
    # -------------------------
    if m in ["till", "glacial till", "till sample", "basal till"]:
        return (
            "Glacial till is inherently heterogeneous, and duplicate RPD values may be elevated due to "
            "grain‑size and mineralogical variability."
        )

    # -------------------------
    # Vegetation
    # -------------------------
    if m in ["vegetation", "plant", "veg", "leaf", "needle"]:
        return (
            "Vegetation samples often show elevated duplicate variability due to heterogeneous organic "
            "content and incomplete digestion of resistant components."
        )

    # -------------------------
    # Talus fines
    # -------------------------
    if m in ["talus fines", "talus", "colluvium"]:
        return (
            "Talus fines commonly exhibit moderate duplicate variability due to mixed lithologies and "
            "variable weathering products."
        )

    # -------------------------
    # Stream sediment
    # -------------------------
    if m in ["stream sediment", "sediment", "fluvial", "ss", "stream sed"]:
        return (
            "Stream sediments are heterogeneous due to hydraulic sorting, and duplicate RPD values may "
            "be elevated for elements concentrated in minor mineral phases."
        )

    # -------------------------
    # Lake sediment
    # -------------------------
    if m in ["lake sediment", "lacustrine"]:
        return (
            "Lake sediments often contain fine clays and organics, which can influence duplicate "
            "precision through natural compositional variability."
        )

    # -------------------------
    # Mixed or unknown
    # -------------------------
    if m in ["mixed", "unknown", "various", "composite"]:
        return (
            "These samples represent a mixed or unspecified matrix. Duplicate precision should be "
            "interpreted with consideration of matrix‑specific heterogeneity and digestion behaviour."
        )

    # -------------------------
    # Fallback
    # -------------------------
    return (
        f"Duplicate precision for samples classified as '{matrix_type}' should be interpreted with "
        "consideration of matrix‑specific heterogeneity and digestion behaviour."
    )


# ------------------------------------------------------------
# METHOD CONTEXT BLOCK
# ------------------------------------------------------------

def method_context(method_code):
    m = str(method_code).upper().strip()

   # ---------------------------------
    # Aqua regia + ICP‑MS (AR‑MS, AR‑ICPMS, ARMS, etc.)
    # ---------------------------------
    if (
        "AR-ICPMS" in m
        or "AR ICPMS" in m
        or "AR-MS" in m
        or "AR MS" in m
        or "ARMS" in m
        or ("AR" in m and "ICP" in m and "MS" in m)
    ):
        return (
            "Aqua regia digestion (HCl–HNO₃) combined with ICP‑MS detection provides high sensitivity "
            "for trace elements. The digestion effectively dissolves sulfides, carbonates, and other "
            "labile hosts, but does not fully decompose silicate minerals or refractory phases such as "
            "zircon, chromite, barite, or monazite. As a result, elements hosted in resistant minerals "
            "may show systematic under‑recovery. ICP‑MS offers low detection limits but is susceptible "
            "to matrix‑dependent polyatomic interferences (e.g., Cl‑based species, oxide/hydroxide "
            "clusters), depending on whether collision/reaction cell technology is used. Precision is "
            "typically 5–10% RSD for analytes present at ≥10× the detection limit, with recoveries "
            "influenced by mineralogy, matrix composition, and interference‑control settings."
        )


    # ---------------------------------
    # Aqua regia + ICP-OES
    # ---------------------------------
    if "AR-ICPOES" in m or "AR ICP-OES" in m or ("AR" in m and "ICP-OES" in m):
        return (
            "Aqua regia digestion (HCl–HNO₃) with ICP‑OES detection is well suited for major, minor, "
            "and some trace elements in geochemical samples. The digestion dissolves sulfides and "
            "labile phases but does not fully break down silicates or refractory minerals. ICP‑OES "
            "is generally more robust than ICP‑MS in high‑TDS matrices and less affected by "
            "mass‑spectrometric polyatomic interferences, though detection limits are higher. "
            "Precision is commonly a few to ~10% RSD for analytes present at ≥10× the detection limit."
        )

    # ---------------------------------
    # Four-acid digestions
    # ---------------------------------
    if "4A" in m or "4-ACID" in m or "4ACID" in m or "4AC" in m:
        return (
            "Four‑acid digestion (HF‑HClO₄‑HNO₃‑HCl) is a near‑total decomposition method capable of "
            "breaking down most silicate, oxide, and sulfide minerals. While generally considered a "
            "robust, high‑recovery digestion for major and trace elements, some highly refractory "
            "phases (e.g., zircon, chromite, barite) may remain partially undissolved, and certain "
            "elements (e.g., As, Sb, Cr, U, Au) can exhibit volatilization losses or solution "
            "instability under specific conditions. Precision is typically a few to ~10% RSD for "
            "most elements at concentrations above ~10× the detection limit, though matrix "
            "composition and mineralogy can influence recoveries for elements hosted in resistant minerals."
        )

    # ---------------------------------
    # Fire assay + AAS
    # ---------------------------------
    if "FA-AAS" in m:
        return (
            "Fire assay with AAS (or instrumental) finish provides high accuracy for Au and, in some methods, "
            "PGEs at low levels. In routine work, precision is commonly on the order of a few to ~10% RSD, with "
            "greater variability near the detection limit."
        )

    # ---------------------------------
    # Fire assay + ICP
    # ---------------------------------
    if "FA-ICP" in m or "FA ICP" in m or "FA-ICPMS" in m or "FA-ICPOES" in m:
        return (
            "Fire assay with ICP‑MS or ICP‑OES finish provides high sensitivity for Au and, depending on "
            "the method, selected PGEs. The fire assay step ensures effective collection of precious metals, "
            "while the ICP finish offers lower detection limits and a broader dynamic range than AAS. Precision "
            "is typically a few to ~10% RSD for Au at concentrations above the method’s practical detection "
            "limit, with increased variability near low‑grade levels or in samples with challenging matrices."
        )

    # ---------------------------------
    # Photon Assay
    # ---------------------------------
    if "PHOTON" in m or "PHOTON ASSAY" in m:
        return (
            "Photon Assay is a non‑destructive, high‑energy X‑ray activation technique used primarily "
            "for gold and sometimes silver. Because no digestion is required, matrix effects are "
            "minimal and precision is typically excellent for well‑prepared pulps. However, coarse "
            "gold, nugget effects, and sample heterogeneity can dominate precision behaviour."
        )

    # ---------------------------------
    # INAA
    # ---------------------------------
    if "INAA" in m:
        return (
            "Instrumental Neutron Activation Analysis (INAA) is a digestion‑free technique with "
            "high potential accuracy for many lithophile and siderophile elements. Matrix effects "
            "are generally minimal and largely limited to neutron and gamma self‑absorption, "
            "while precision depends mainly on neutron flux and counting statistics; duplicate "
            "variability often reflects mineralogical heterogeneity rather than analytical error."
        )

    # ---------------------------------
    # Fallback
    # ---------------------------------
    return (
        f"The {method_code} method was used. Typical performance characteristics include digestion "
        "completeness considerations, matrix effects, and concentration‑dependent precision."
    )


# ------------------------------------------------------------
# QC METRIC SUMMARIES
# ------------------------------------------------------------

def summarize_crm(crm_results):
    if crm_results is None or crm_results.empty:
        return {
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
            "crm_fail_pattern": "none"
        }

    df = crm_results.copy()

    # Evaluable rows = numeric recovery + OK/Fail
    numeric_mask = pd.to_numeric(df["Recovery"], errors="coerce").notna()
    status_mask = df["CRM_Status"].isin(["OK", "Fail"])
    evaluable = df[numeric_mask & status_mask]

    if evaluable.empty:
        return {
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
            "crm_fail_pattern": "none"
        }

    failures = evaluable[evaluable["CRM_Status"] == "Fail"]

    # CRM run counts
    crm_runs = df["CRM"].nunique()
    crm_unique = df["CRM"].str.replace(r"\s*\(\w.*", "", regex=True).nunique()

    # Group failures by CRM and analyte
    fail_by_crm = failures.groupby("CRM")["Analyte"].apply(list).to_dict()
    fail_by_analyte = failures.groupby("Analyte")["CRM"].apply(list).to_dict()

    # Count how many failures each CRM contributed
    crm_fail_counts = {crm: len(analytes) for crm, analytes in fail_by_crm.items()}
    crm_fail_unique = len(crm_fail_counts)

    # Determine pattern
    if crm_fail_unique == 0:
        crm_fail_pattern = "none"
    elif crm_fail_unique == 1:
        crm_fail_pattern = "single_crm"
    else:
        crm_fail_pattern = "multi_crm"

    # Group failures by analyte with min/max recovery
    fail_grouped = {}
    for analyte, group in failures.groupby("Analyte"):
        rec = pd.to_numeric(group["Recovery"], errors="coerce")
        fail_grouped[analyte] = {
            "count": len(group),
            "min": float(rec.min()),
            "max": float(rec.max())
        }

    # Build readable list
    fail_list_grouped = []
    for analyte, info in fail_grouped.items():
        if info["count"] == 1:
            fail_list_grouped.append(f"{analyte}: {info['min']:.1f}%")
        else:
            fail_list_grouped.append(
                f"{analyte}: {info['min']:.1f}–{info['max']:.1f}% ({info['count']} runs)"
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
        "crm_fail_pattern": crm_fail_pattern
    }


def summarize_duplicates(dup_results):
    if dup_results is None or dup_results.empty:
        return {"count": 0, "failures": 0, "failed": [], "skipped": 0}

    # Only analytes with numeric RPD values count toward precision evaluation
    dup_numeric = dup_results[pd.to_numeric(dup_results["RPD"], errors="coerce").notna()]
    skipped = len(dup_results) - len(dup_numeric)

    if dup_numeric.empty:
        return {"count": 0, "failures": 0, "failed": [], "skipped": skipped}

    # Failures come from Status == "Fail"
    failures = dup_numeric[dup_numeric["Status"].str.upper() == "FAIL"]

    return {
        "count": len(dup_numeric),
        "failures": len(failures),
        "failed": [
            f"{row['Analyte']} ({row['RPD']:.1f}% RPD)"
            for _, row in failures.iterrows()
        ],
        "skipped": skipped
    }


def summarize_blanks(blank_results):
    if blank_results is None or blank_results.empty:
        return {"count": 0, "failures": 0, "failed": []}

    # Use Status
    failures = blank_results[blank_results["Blank_Status"].str.upper() == "FAIL"]

    return {
        "count": len(blank_results),
        "failures": len(failures),
        "failed": [
            f"{row['Analyte']} ({row['Average']} > DL {row['DL']})"
            for _, row in failures.iterrows()
        ]
    }


# ------------------------------------------------------------
# INTERPRETATION BLOCKS
# ------------------------------------------------------------

def interpret_crm(metrics, crm_sample_count):
    if crm_sample_count == 0:
        return "The CRM component of this batch contains no CRM samples."

    # No failures
    if metrics["failures"] == 0:
        return (
            f"The CRM results show that all {crm_sample_count} CRM samples fall within expected "
            "recovery ranges for analytes above the evaluation threshold (typically ≥10× DL), "
            "indicating stable digestion performance and consistent instrument calibration."
        )

    grouped_lines = "\n".join(f"  • {line}" for line in metrics['fail_list_grouped'])

    # Pattern interpretation
    if metrics["crm_fail_pattern"] == "single_crm":
        pattern_text = (
            "The CRM deviations originate from a single CRM material, a pattern that often reflects "
            "CRM‑specific behaviour (e.g., matrix mismatch or certified value uncertainty) rather "
            "than a batch‑wide analytical issue."
        )
    elif metrics["crm_fail_pattern"] == "multi_crm":
        pattern_text = (
            f"The CRM deviations occur across {metrics['crm_fail_unique']} different CRMs. "
            "When multiple CRMs show similar patterns, this may indicate method‑level effects such "
            "as digestion inefficiency, calibration drift, or interference‑related bias."
        )
    else:
        pattern_text = (
            "The CRM deviations do not follow a clear CRM‑specific or multi‑CRM pattern. Review the "
            "affected analytes for known digestion limitations or interference‑related behaviour."
        )

    return (
        f"The CRM results show {metrics['failures']} analyte‑level deviations across "
        f"{crm_sample_count} CRM runs. Deviations by analyte:\n\n"
        f"{grouped_lines}\n\n"
        f"{pattern_text}\n\n"
        "When CRM deviations occur, review digestion conditions, calibration stability, and "
        "interference‑control settings to confirm whether the method is performing within its "
        "expected analytical envelope."
    )



def interpret_duplicates(metrics, dup_sample_count, rpd_tol):
    """
    Interpret duplicate precision results using the user-defined RPD tolerance.
    """

    # No duplicates at all
    if dup_sample_count == 0:
        return (
            "No duplicate samples were included in this batch, so analytical precision "
            "could not be evaluated."
        )

    # Duplicates present, but all analytes < 10× DL
    if metrics["count"] == 0:
        return (
            "One duplicate sample was included, but all analytes were below 10× DL, "
            "so RPD‑based precision could not be evaluated."
        )

    # All analytes above 10× DL meet the tolerance
    if metrics["failures"] == 0:
        return (
            f"The duplicate samples show that all analytes above 10× DL meet the ≤{rpd_tol}% RPD "
            "precision criterion, indicating stable analytical precision for this batch."
        )

    # Failure case
    msg = (
        f"{metrics['failures']} analytes in the duplicate sample exceed the {rpd_tol}% RPD threshold. "
        f"Duplicate RPD values > {rpd_tol}% may reflect sample heterogeneity, low‑grade variability, or "
        "analytical precision limits. Affected analytes include:\n"
        + "\n".join(f"  • {a}" for a in metrics["failed"])
        + "\n\n"
        "When duplicate failures occur, they typically indicate variability in "
        "sample preparation, subsampling, or analytical precision rather than systematic analytical bias."
    )

    # Skipped analytes (<10× DL or BDL)
    if metrics.get("skipped", 0) > 0:
        msg += (
            f"\n\nAn additional {metrics['skipped']} analytes were below 10× DL or involved "
            "BDL values and were excluded from precision evaluation."
        )

    return msg


def interpret_blanks(metrics, blank_sample_count):
    if blank_sample_count == 0:
        return "The blank component of this batch contains no blank samples."

    if metrics["failures"] == 0:
        return (
            "The blank results show all analytes below detection limits, indicating no evidence of "
            "laboratory contamination or instrument carryover."
        )

    return (
        f"The blank results show {metrics['failures']} analytes exceeding blank thresholds, "
        "suggesting possible low‑level contamination, memory effects, or instrument carryover. "
        "Affected analytes include:\n"
        + "\n".join(f"  • {a}" for a in metrics["failed"])
        + "\n\n"
        "When blank exceedances occur, review recent high‑grade samples, "
        "rinse sequences, and contamination‑control procedures. Consider whether affected analytes "
        "could influence the interpretation of low‑grade samples in this batch."
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
    bdl_sub_rule=None
):

    text = []

    # ------------------------------------------------------------
    # Header
    # ------------------------------------------------------------
    text.append(f"QC Summary for {file_name} (Metadata: {metadata_name}, Date: {report_date})")
    text.append(f"Laboratory: {lab_name}")
    text.append("")

    # ------------------------------------------------------------
    # Batch summary
    # ------------------------------------------------------------
    batch = compute_batch_summary(df_qc, crm_results, dup_results)

    text.append(
        f"This batch includes {batch['total_samples']} total samples, consisting of "
        f"{batch['crm_samples']} CRM samples, {batch['duplicate_samples']} duplicate samples, "
        f"and {batch['blank_samples']} blanks."
    )
    text.append("")
    
    # Transition
    text.append(
    "Understanding the digestion chemistry and detection technique is important for interpreting "
    "CRM recoveries, duplicate precision, and blank performance. The method used for this batch "
    "is summarized below."
    )
    text.append("")


    # ------------------------------------------------------------
    # Method / Digestion context
    # ------------------------------------------------------------
    text.append(method_context(method_code))
    text.append("")

    # ------------------------------------------------------------
    # CRM behaviour → CRM summary -> Tolerance
    # ------------------------------------------------------------
    text.append("CRM Behaviour:")
    text.append(
        "CRM performance provides insight into digestion consistency, calibration stability, "
        "interference behaviour, and whether the method is operating within its expected analytical "
        "envelope."
    )
    text.append("")
    text.append(f"CRM tolerance applied: {crm_low_tol:.0f}–{crm_high_tol:.0f}% recovery.")
    text.append("• CRM Recovery (%):")
    text.append("  Recovery % = (Measured Value / Certified Value) × 100")
    text.append("• CRM Bias (%):")
    text.append("  Bias % = ((Measured Value – Certified Value) / Certified Value) × 100")
    text.append("")


    crm_metrics = summarize_crm(crm_results)
    text.append(interpret_crm(crm_metrics, batch['crm_samples']))
    text.append("")

    # ------------------------------------------------------------
    # Duplicate behaviour → Duplicate summary -> Tolerance
    # ------------------------------------------------------------
    text.append("Duplicate Behaviour:")
    text.append(
        "Duplicate samples evaluate analytical precision. For analytes present at ≥10× the detection "
        "limit, precision is typically 5–10% RSD. Elements near the detection limit, or are sensitive to "
        "adsorption, partial digestion, or matrix effects commonly show higher RPD values."
    )
    text.append("")
    text.append(f"Duplicate tolerance applied: ≤{duplicate_rpd_tol:.0f}% RPD.")
    text.append("• Duplicate Relative Percent Difference (RPD):")
    text.append("  RPD % = |Sample1 – Sample2| / ((Sample1 + Sample2) / 2) × 100")
    text.append("")

    dup_metrics = summarize_duplicates(dup_results)
    text.append(
        interpret_duplicates(
            dup_metrics,
            batch['duplicate_samples'],
            duplicate_rpd_tol
        )
    )

    text.append("")

    # Matrix-aware duplicate precision context
    text.append(matrix_context(matrix_type))
    text.append("")

    # ------------------------------------------------------------
    # Blank behaviour → Blank summary -> Tolerance
    # ------------------------------------------------------------
    text.append("Blank Behaviour:")
    text.append(
        "Blank samples help identify contamination, memory effects, and instrument carryover. "
        "Exceedances should be considered when interpreting low‑grade sample results, particularly "
        "for coarse blanks."
    )
    text.append("")
    text.append(f"Blank tolerance applied: values > {blank_tol_factor:.1f}× DL flagged.")
    text.append(f"BDL substitution rule applied: {bdl_sub_rule}.")
    text.append("• Blank Mean:")
    text.append("  Blank Mean = Σ(blank values) / n")
    text.append("• Blank Standard Deviation (SD):")
    text.append("  Blank SD = sqrt( Σ(x – mean)² / (n – 1) )")
    text.append("")

    blk_metrics = summarize_blanks(blank_results)
    text.append(interpret_blanks(blk_metrics, batch['blank_samples']))
    text.append("")

    # ------------------------------------------------------------
    # Disclaimer
    # ------------------------------------------------------------
    text.append(
        "Note: QC results reflect internal laboratory quality‑control performance for this batch. "
        "They highlight patterns that may warrant further review but should be interpreted alongside "
        "laboratory documentation and project context."
    )
    text.append("")

    # ------------------------------------------------------------
    # Status Definitions
    # ------------------------------------------------------------
    text.append(
        "Status Definitions:\n"
        "- OK: Assay results fall within the defined tolerance.\n"
        "- Fail: Assay results exceed the defined tolerance.\n"
        "- Fail_RPD: Duplicate RPD exceeds the precision tolerance.\n"
        "- BDL_Substitution: One value is below the detection limit and a substitution was applied.\n"
        "- BothBDL: Both values are below the detection limit; evaluation is not meaningful.\n"
        "- Below10xDL: Values are below 10× the detection limit; evaluation is not meaningful.\n"
        "- Needs Investigation: Conditions prevent reliable evaluation (e.g., certified ≥ DL but measured < DL, or borderline blank values).\n"
        "- NotApplicable: Certified value or both measurements are below DL; evaluation is not required.\n"
        "- NotEvaluated: Required assay data are missing."
    )
    text.append("")

    return "\n".join(text)