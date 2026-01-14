import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ============================================================
# Helper: enforce certificate order + add placeholders
# ============================================================
def enforce_certificate_order(df, certificate_order, value_cols, status_col):
    df = df.copy()

    # Identify missing analytes
    missing = set(certificate_order) - set(df["Analyte"])

    if missing:
        placeholder = pd.DataFrame({
            "Analyte": list(missing),
            **{col: [np.nan] * len(missing) for col in value_cols},
            status_col: ["Not Evaluated"] * len(missing)
        })
        df = pd.concat([df, placeholder], ignore_index=True)

    # Reindex to certificate order
    df["Analyte"] = pd.Categorical(df["Analyte"], categories=certificate_order, ordered=True)
    df = df.sort_values("Analyte")

    return df


# ============================================================
# Colour-blind friendly palette (Okabe–Ito)
# ============================================================
OKABE_ITO = {
    "OK": "#56B4E9",                 # sky blue
    "Fail": "#E69F00",               # orange
    "Fail_RPD": "#E69F00",           # orange
    "NeedsInvestigation": "#F0E442", # yellow
    "BDL_Substitution": "#56B4E9",   # sky blue (same as OK)
    "NotApplicable": "#999999",      # grey
    "NotEvaluated": "#000000",       # black
    "Line": "#E69F00",               # orange
}

# ============================================================
# CRM RECOVERY PLOT
# ============================================================
def plot_crm_recovery(crm_summary, certificate_order, low_tol=80, high_tol=120):

    # Work on a copy for plotting only
    df = crm_summary.copy()

    # 1) Normalize raw statuses → internal codes
    crm_status_map = {
        "OK": "OK",
        "Fail": "Fail",
        "NotApplicable": "NotApplicable",
        "NotEvaluated": "NotEvaluated",
        "Below10xDL": "NotEvaluated",
        "Needs Investigation": "NeedsInvestigation",
    }

    df["PlotStatus"] = df["CRM_FinalStatus"].map(crm_status_map).fillna("NotEvaluated")

    # ------------------------------------------------------------
    # 2) Plot-only override:
    #    If numeric recovery is inside tolerance but status is Fail,
    #    show as NeedsInvestigation instead of Fail.
    # ------------------------------------------------------------
    good_zone = df["CRM_Recovery"].between(low_tol, high_tol, inclusive="both")

    df.loc[
        good_zone & (df["PlotStatus"] == "Fail"),
        "PlotStatus"
    ] = "NeedsInvestigation"

    # ------------------------------------------------------------
    # 3) Enforce certificate order
    # ------------------------------------------------------------
    df = enforce_certificate_order(
        df,
        certificate_order,
        value_cols=["CRM_Recovery"],
        status_col="PlotStatus"
    )

    analytes = df["Analyte"].tolist()
    recovery = df["CRM_Recovery"].tolist()

    plt.figure(figsize=(14, 6))
    plotted_statuses = set()

    # ------------------------------------------------------------
    # 4) Plot lollipops
    # ------------------------------------------------------------
    for i, (y, status) in enumerate(zip(recovery, df["PlotStatus"])):
        color = OKABE_ITO.get(status, OKABE_ITO["NotEvaluated"])
        y_plot = y if not pd.isna(y) else 0

        plt.plot([i, i], [0, y_plot], color=color, linewidth=1.2, alpha=0.7)
        plt.scatter(i, y_plot, color=color, s=60, edgecolor="black", linewidth=0.5)

        plotted_statuses.add(status)

    # Tolerance lines
    plt.axhline(low_tol, color=OKABE_ITO["Line"], linestyle="--", linewidth=1)
    plt.axhline(high_tol, color=OKABE_ITO["Line"], linestyle="--", linewidth=1)

    plt.xticks(range(len(analytes)), analytes, rotation=90)
    plt.ylabel("Recovery (%)")
    plt.title("CRM Recovery (Status-Coloured Lollipop Plot)")

    # ------------------------------------------------------------
    # 5) Legend
    # ------------------------------------------------------------
    legend_items = {
        "OK": ("OK", OKABE_ITO["OK"]),
        "Fail": ("Fail", OKABE_ITO["Fail"]),
        "NeedsInvestigation": ("Needs Investigation", OKABE_ITO["NeedsInvestigation"]),
        "NotApplicable": ("Not Applicable", OKABE_ITO["NotApplicable"]),
        "NotEvaluated": ("Not Evaluated", OKABE_ITO["NotEvaluated"]),
        "Line": ("Tolerance", OKABE_ITO["Line"]),
    }

    handles = []
    for code, (label, color) in legend_items.items():
        if code == "Line" or code in plotted_statuses:
            handles.append(
                plt.Line2D(
                    [0], [0],
                    marker='o' if code != "Line" else None,
                    linestyle='--' if code == "Line" else 'none',
                    color=color,
                    markerfacecolor=color if code != "Line" else None,
                    markeredgecolor='black' if code != "Line" else None,
                    label=label,
                )
            )

    plt.legend(handles=handles, title="CRM Status",
               bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    return plt.gcf()


# ============================================================
# DUPLICATE RPD PLOT
# ============================================================
def plot_duplicate_rpd(dup_results, certificate_order, rpd_tolerance=30.0):

    df = dup_results.copy()

    # ------------------------------------------------------------------
    # 1) Normalize Duplicate_Status to internal plotting codes
    #    (no spaces; match OKABE_ITO keys)
    # ------------------------------------------------------------------
    status_map = {
        "OK": "OK",
        "Fail": "Fail_RPD",
        "Fail_RPD": "Fail_RPD",
        "BDL_Substitution": "BDL_Substitution",
        "BothBDL": "NotEvaluated",
        "Below10xDL": "NotEvaluated",
        "NotApplicable": "NotApplicable",
        "NotEvaluated": "NotEvaluated",
        "Needs Investigation": "NeedsInvestigation",
    }

    df["PlotStatus"] = df["Duplicate_Status"].map(status_map).fillna("NotEvaluated")

    # ------------------------------------------------------------------
    # 2) Enforce certificate order + placeholders
    # ------------------------------------------------------------------
    df = enforce_certificate_order(
        df,
        certificate_order,
        value_cols=["Duplicate_RPD"],
        status_col="PlotStatus",
    )

    analytes = df["Analyte"].tolist()
    x_positions = {a: i for i, a in enumerate(analytes)}

    plt.figure(figsize=(14, 6))

    # Track only statuses that actually get plotted
    plotted_statuses = set()

    # ------------------------------------------------------------------
    # 3) Plot lollipops, colouring by PlotStatus
    # ------------------------------------------------------------------
    for _, row in df.iterrows():
        x = x_positions[row["Analyte"]]
        # If Duplicate_RPD is missing, treat as 0 for plotting but still track status
        y = row["Duplicate_RPD"] if not pd.isna(row["Duplicate_RPD"]) else 0
        status = row["PlotStatus"]

        # Look up colour by internal code; fall back to NotEvaluated (black)
        color = OKABE_ITO.get(status, OKABE_ITO["NotEvaluated"])

        plt.plot([x, x], [0, y], color=color, linewidth=1.2, alpha=0.7)
        plt.scatter(x, y, color=color, s=60, edgecolor="black", linewidth=0.5)

        plotted_statuses.add(status)

    # RPD tolerance line
    plt.axhline(rpd_tolerance, color=OKABE_ITO["Line"], linestyle="--", linewidth=1)

    plt.xticks(range(len(analytes)), analytes, rotation=90)
    plt.ylabel("RPD (%)")
    plt.title("Duplicate RPD (Status-Coloured Lollipop Plot)")

    # ------------------------------------------------------------------
    # 4) Legend: map internal codes -> human labels and colours
    #    Only include codes that actually appear in plotted_statuses
    # ------------------------------------------------------------------
    legend_items = {
        "OK": ("OK", OKABE_ITO["OK"]),
        "Fail_RPD": ("Fail RPD", OKABE_ITO["Fail_RPD"]),
        "BDL_Substitution": ("BDL Substitution", OKABE_ITO["BDL_Substitution"]),
        "NeedsInvestigation": ("Needs Investigation", OKABE_ITO["NeedsInvestigation"]),
        "NotApplicable": ("Not Applicable", OKABE_ITO["NotApplicable"]),
        "NotEvaluated": ("Not Evaluated", OKABE_ITO["NotEvaluated"]),
        "Line": ("Tolerance", OKABE_ITO["Line"]),
    }

    handles = []
    for code, (label, color) in legend_items.items():
        if code == "Line" or code in plotted_statuses:
            handles.append(
                plt.Line2D(
                    [0], [0],
                    marker='o' if code != "Line" else None,
                    linestyle='--' if code == "Line" else 'none',
                    color=color,
                    markerfacecolor=color if code != "Line" else None,
                    markeredgecolor='black' if code != "Line" else None,
                    label=label,
                )
            )

    plt.legend(handles=handles, title="Duplicate Status",
               bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    return plt.gcf()


# ============================================================
# BLANK LEVELS PLOT
# ============================================================
def plot_blank_levels(blank_results, certificate_order, tolerance_factor=3.0):

    df = blank_results.copy()

    required = ["Analyte", "Average", "DL", "Blank_Status"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        print(f"Missing columns in blank_results: {missing_cols}")
        return

    # ------------------------------------------------------------
    # 1) Normalize Blank_Status to internal plotting codes
    # ------------------------------------------------------------
    blank_status_map = {
        "OK": "OK",
        "Fail": "Fail",
        "Needs Investigation": "NeedsInvestigation",
        "NotEvaluated": "NotEvaluated",
    }

    df["PlotStatus"] = df["Blank_Status"].map(blank_status_map).fillna("NotEvaluated")

    # ------------------------------------------------------------
    # 2) Enforce certificate order + placeholders
    # ------------------------------------------------------------
    df = enforce_certificate_order(
        df,
        certificate_order,
        value_cols=["Average", "DL"],
        status_col="PlotStatus"
    )

    analytes = df["Analyte"].tolist()
    avg = df["Average"].tolist()
    dl = df["DL"].tolist()

    tolerance = [(d * tolerance_factor) if not pd.isna(d) else np.nan for d in dl]

    plt.figure(figsize=(14, 6))

    # Track only statuses that actually appear on the plot
    plotted_statuses = set()

    # ------------------------------------------------------------
    # 3) Plot lollipops
    # ------------------------------------------------------------
    for i, (y, status) in enumerate(zip(avg, df["PlotStatus"])):
        color = OKABE_ITO.get(status, OKABE_ITO["NotEvaluated"])
        y_plot = y if not pd.isna(y) else 0

        plt.plot([i, i], [0, y_plot], color=color, linewidth=1.2, alpha=0.7)
        plt.scatter(i, y_plot, color=color, s=60, edgecolor="black", linewidth=0.5)

        plotted_statuses.add(status)

    # DL and tolerance lines
    plt.plot(range(len(analytes)), dl, color=OKABE_ITO["Line"], linestyle="-", linewidth=1.2)
    plt.plot(range(len(analytes)), tolerance, color=OKABE_ITO["Line"], linestyle="--", linewidth=1.2)

    plt.xticks(range(len(analytes)), analytes, rotation=90)
    plt.ylabel("Blank Value")
    plt.title("Blank Levels (Status-Coloured Lollipop Plot)")

    # ------------------------------------------------------------
    # 4) Legend: internal codes → human labels
    # ------------------------------------------------------------
    legend_items = {
        "OK": ("OK", OKABE_ITO["OK"]),
        "Fail": ("Fail", OKABE_ITO["Fail"]),
        "NeedsInvestigation": ("Needs Investigation", OKABE_ITO["NeedsInvestigation"]),
        "NotApplicable": ("Not Applicable", OKABE_ITO["NotApplicable"]),
        "NotEvaluated": ("Not Evaluated", OKABE_ITO["NotEvaluated"]),
        "DL": ("DL", OKABE_ITO["Line"]),
        "Tolerance": ("Tolerance", OKABE_ITO["Line"]),
    }

    handles = []
    for code, (label, color) in legend_items.items():
        if code in ["DL", "Tolerance"] or code in plotted_statuses:
            handles.append(
                plt.Line2D(
                    [0], [0],
                    marker='o' if code not in ["DL", "Tolerance"] else None,
                    linestyle='-' if code == "DL" else '--' if code == "Tolerance" else 'none',
                    color=color,
                    markerfacecolor=color if code not in ["DL", "Tolerance"] else None,
                    markeredgecolor='black' if code not in ["DL", "Tolerance"] else None,
                    label=label,
                )
            )

    plt.legend(handles=handles, title="Blank Status",
               bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    return plt.gcf()