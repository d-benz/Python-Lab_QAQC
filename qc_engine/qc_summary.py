import pandas as pd
import numpy as np


# ============================================================
# Safe merge helper
# ============================================================
def safe_merge(left, right, on_cols):
    """Merge two QC tables safely. If right is empty, return left unchanged."""
    if right is None or len(right) == 0:
        return left
    return pd.merge(left, right, on=on_cols, how="left")


# ============================================================
# Status normalization
# ============================================================
def normalize_status(x):
    """Normalize QC status strings for final evaluation."""
    if pd.isna(x):
        return "NotEvaluated"
    return str(x)


# ============================================================
# Final QC flag logic
# ============================================================
def final_flag(row):

    crm = normalize_status(row.get("CRM_FinalStatus"))
    dup = normalize_status(row.get("Duplicate_Status"))
    blank = normalize_status(row.get("Blank_Status"))

    # --- Hard Fail ---
    if crm == "Fail" or dup == "Fail" or blank == "Fail":
        return "Fail"

    # --- Needs Investigation ---
    if crm == "Needs Investigation":
        return "Needs Investigation"

    if dup in ["BDL_Substitution", "NotEvaluated"]:
        return "Needs Investigation"

    if blank in ["Needs Investigation", "NotEvaluated"]:
        return "Needs Investigation"

    # --- Pass ---
    return "Pass"


# ============================================================
# Build QC Summary
# ============================================================
def build_qc_summary(crm_results, dup_results, blank_results):
    """
    Build a unified QC summary table from CRM, Duplicate, and Blank modules.
    Uses updated CRM logic and updated Duplicate logic (10× DL rule).
    """

    crm = crm_results.copy() if crm_results is not None else pd.DataFrame()
    dup = dup_results.copy() if dup_results is not None else pd.DataFrame()
    blank = blank_results.copy() if blank_results is not None else pd.DataFrame()

    # ============================================================
    # --- Reduce CRM table ---
    # ============================================================
    if not crm.empty:

        # Ensure CRM_Status exists
        if "CRM_Status" not in crm.columns:
            if "Status" in crm.columns:
                crm = crm.rename(columns={"Status": "CRM_Status"})
            else:
                crm["CRM_Status"] = "NotEvaluated"

        # Convert numeric fields
        crm["Recovery_num"] = pd.to_numeric(crm["Recovery"], errors="coerce")
        crm["Bias_num"] = pd.to_numeric(crm["Bias"], errors="coerce")

        # CRM reducer
        def reduce_crm(group):
            statuses = group["CRM_Status"].tolist()

            return pd.Series({
                "CRM_Recovery": group["Recovery_num"].mean(),
                "CRM_Bias": group["Bias_num"].mean(),
                "CRM_PassCount": statuses.count("OK"),
                "CRM_FailCount": statuses.count("Fail"),
                "CRM_NeedsInvestigationCount": statuses.count("Needs Investigation"),
                "CRM_Below10xDLCount": statuses.count("Below10xDL"),
                "CRM_NotApplicableCount": statuses.count("NotApplicable"),
                "CRM_NotEvaluatedCount": statuses.count("NotEvaluated"),
                "CRM_TotalEvaluated": (
                    statuses.count("OK") +
                    statuses.count("Fail") +
                    statuses.count("Needs Investigation")
                ),
                "CRM_FinalStatus": compute_crm_final_status(statuses)
            })


        # Final CRM status logic
        def compute_crm_final_status(statuses):
            fail_count = statuses.count("Fail")
            ni_count = statuses.count("Needs Investigation")
            ok_count = statuses.count("OK")

            # Hard fail: 2 or more CRM failures
            if fail_count >= 2:
                return "Fail"

            # Needs Investigation: exactly 1 fail OR any NI
            if fail_count == 1:
                return "Needs Investigation"

            if ni_count > 0:
                return "Needs Investigation"

            # Pass
            if ok_count > 0:
                return "OK"

            # Not Applicable (all below DL or NA)
            if all(s in ["NotApplicable", "Below10xDL"] for s in statuses):
                return "NotApplicable"

            return "NotEvaluated"




        crm_small = (
            crm.groupby(["Analyte", "Unit"], as_index=False)
               .apply(reduce_crm)
               .reset_index(drop=True)
        )

    else:
        crm_small = pd.DataFrame(columns=[
            "Analyte", "Unit",
            "CRM_Recovery", "CRM_Bias",
            "CRM_PassCount", "CRM_FailCount",
            "CRM_NeedsInvestigationCount",
            "CRM_NotApplicableCount", "CRM_NotEvaluatedCount",
            "CRM_TotalEvaluated", "CRM_FinalStatus"
        ])

    # ============================================================
    # --- Reduce Duplicate table (updated for 10× DL rule) ---
    # ============================================================
    if not dup.empty:

        if "Duplicate_Status" not in dup.columns:
            if "Status" in dup.columns:
                dup = dup.rename(columns={"Status": "Duplicate_Status"})
            else:
                dup["Duplicate_Status"] = "NotEvaluated"

        dup["RPD_num"] = pd.to_numeric(dup["RPD"], errors="coerce")

        def reduce_dup(group):
            statuses = group["Duplicate_Status"].tolist()

            return pd.Series({
                "Duplicate_RPD": group["RPD_num"].mean(),
                "Duplicate_PassCount": statuses.count("OK"),
                "Duplicate_FailCount": statuses.count("Fail_RPD"),
                "Duplicate_BDLSubCount": statuses.count("BDL_Substitution"),
                "Duplicate_BothBDLCount": statuses.count("BothBDL"),
                "Duplicate_Below10xDLCount": statuses.count("Below10xDL"),
                "Duplicate_NotEvaluatedCount": statuses.count("NotEvaluated"),
                "Duplicate_TotalEvaluated": (
                    statuses.count("OK") +
                    statuses.count("Fail_RPD")
                ),
                "Duplicate_Status": compute_dup_final_status(statuses),
            })

        def compute_dup_final_status(statuses):
            if "Fail_RPD" in statuses:
                return "Fail"
            if "BDL_Substitution" in statuses:
                return "Needs Investigation"
            if "NotEvaluated" in statuses:
                return "Needs Investigation"
            if "OK" in statuses:
                return "OK"
            if all(s in ["BothBDL", "Below10xDL"] for s in statuses):
                return "NotApplicable"
            return "NotEvaluated"

        dup_small = (
            dup.groupby(["Analyte", "Unit"], as_index=False)
               .apply(reduce_dup)
               .reset_index(drop=True)
        )

    else:
        dup_small = pd.DataFrame(columns=[
            "Analyte", "Unit",
            "Duplicate_RPD",
            "Duplicate_PassCount", "Duplicate_FailCount",
            "Duplicate_BDLSubCount", "Duplicate_BothBDLCount",
            "Duplicate_Below10xDLCount", "Duplicate_NotEvaluatedCount",
            "Duplicate_TotalEvaluated", "Duplicate_Status"
        ])

    # ============================================================
    # --- Reduce Blank table ---
    # ============================================================
    if not blank.empty:

        if "Blank_Status" not in blank.columns:
            if "Status" in blank.columns:
                blank = blank.rename(columns={"Status": "Blank_Status"})
            else:
                blank["Blank_Status"] = "NotEvaluated"

        blank_small = blank[[
            "Analyte", "Unit", "Average", "StDev", "Blank_Status"
        ]].rename(columns={
            "Average": "Blank_Average",
            "StDev": "Blank_StDev",
        })

    else:
        blank_small = pd.DataFrame(columns=[
            "Analyte", "Unit",
            "Blank_Average", "Blank_StDev", "Blank_Status"
        ])

    # ============================================================
    # --- Merge all QC types ---
    # ============================================================
    summary = crm_small.copy()
    summary = safe_merge(summary, dup_small, on_cols=["Analyte", "Unit"])
    summary = safe_merge(summary, blank_small, on_cols=["Analyte", "Unit"])

    # ============================================================
    # --- Compute final QC flag ---
    # ============================================================
    summary["Final_QC_Flag"] = summary.apply(final_flag, axis=1)

    # ============================================================
    # --- Order columns ---
    # ============================================================
    col_order = [
        "Analyte", "Unit",

        "CRM_Recovery", "CRM_Bias",
        "CRM_PassCount", "CRM_FailCount",
        "CRM_NeedsInvestigationCount", "CRM_Below10xDLCount",
        "CRM_NotApplicableCount", "CRM_NotEvaluatedCount",
        "CRM_TotalEvaluated", "CRM_FinalStatus",

        "Duplicate_RPD", "Duplicate_Status",
        "Duplicate_PassCount", "Duplicate_FailCount",
        "Duplicate_BDLSubCount", "Duplicate_BothBDLCount",
        "Duplicate_Below10xDLCount", "Duplicate_NotEvaluatedCount",
        "Duplicate_TotalEvaluated",

        "Blank_Average", "Blank_StDev", "Blank_Status",

        "Final_QC_Flag",
    ]

    summary = summary[col_order]

    return summary