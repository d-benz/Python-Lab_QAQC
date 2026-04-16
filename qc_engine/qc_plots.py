import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import yaml
import os

# Load config
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# ============================================================
# Colour-blind friendly palette (Okabe-Ito)
# ============================================================
OKABE_ITO = config['plot_colors']

# Distinct line colours for CRM materials (colour-blind safe)
CRM_LINE_COLORS = config['crm_line_colors']

# Mapping raw status values to standardized plot status codes.
STATUS_MAP = config.get('status_map', {
    'OK': 'OK',
    'Fail': 'Fail',
    'Fail_RPD': 'Fail_RPD',
    'BDL_Substitution': 'BDL_Substitution',
    'Needs Investigation': 'NeedsInvestigation',
    'BothBDL': 'NotEvaluated',
    'Below10xDL': 'NotEvaluated',
    'NotApplicable': 'NotApplicable',
    'NotEvaluated': 'NotEvaluated',
})


# ============================================================
# Helper: enforce certificate order + add placeholders
# ============================================================
def enforce_certificate_order(df, certificate_order, value_cols, status_col):
    df = df.copy()

    missing = set(certificate_order) - set(df["Analyte"])

    if missing:
        placeholder = pd.DataFrame({
            "Analyte": list(missing),
            **{col: [np.nan] * len(missing) for col in value_cols},
            status_col: ["NotEvaluated"] * len(missing),
        })
        df = pd.concat([df, placeholder], ignore_index=True)

    df["Analyte"] = pd.Categorical(
        df["Analyte"], categories=certificate_order, ordered=True
    )
    df = df.sort_values("Analyte")

    return df


# ============================================================
# CRM RECOVERY LOLLIPOP PLOT
# ============================================================
def plot_crm_recovery(crm_results, certificate_order, low_tol=80, high_tol=120):

    df = crm_results.copy()

    # Normalize status values to internal plot codes
    if "CRM_Status" in df.columns:
        status_col = "CRM_Status"
    elif "CRM_FinalStatus" in df.columns:
        status_col = "CRM_FinalStatus"
    else:
        status_col = None

    if status_col is not None:
        df["PlotStatus"] = df[status_col].map(STATUS_MAP).fillna("NotEvaluated")
    else:
        df["PlotStatus"] = "NotEvaluated"

    # Normalize recovery values
    df["Recovery_num"] = pd.to_numeric(df["Recovery"], errors="coerce")

    # Build CRM run labels for grouping
    if "CRM_Index" in df.columns:
        df["CRM_Run"] = (
            df["CRM"].astype(str)
            + " #"
            + (pd.to_numeric(df["CRM_Index"], errors="coerce").fillna(0).astype(int) + 1).astype(str)
        )
    else:
        df["CRM_Run"] = df["CRM"].astype(str)

    # Enforce certificate order
    df = enforce_certificate_order(
        df,
        certificate_order,
        value_cols=["Recovery_num"],
        status_col="PlotStatus"
    )

    spacing = 1.5
    analytes = certificate_order
    analyte_positions = {a: i * spacing for i, a in enumerate(analytes)}

    # Setup markers and colors for CRM materials
    marker_shapes = ["o", "s", "D", "^", "v", "<", ">", "P", "X"]
    crm_list = sorted(df["CRM"].dropna().unique())
    crm_marker = {crm: marker_shapes[i % len(marker_shapes)] for i, crm in enumerate(crm_list)}

    # Create figure matching Duplicate and Blank plot width
    plt.figure(figsize=(14, 6))
    plotted_statuses = set()
    seen_crm_labels = set()

    for analyte, group in df.groupby("Analyte", observed=True):
        if pd.isna(analyte):
            continue

        unique_runs = group["CRM_Run"].unique().tolist()
        n_runs = len(unique_runs)
        if n_runs > 1:
            offsets = np.linspace(-0.15, 0.15, n_runs)
        else:
            offsets = [0.0]
        run_offset = dict(zip(unique_runs, offsets))

        x_base = analyte_positions[analyte]
        for _, row in group.iterrows():
            x = x_base + run_offset.get(row["CRM_Run"], 0.0)
            y = row["Recovery_num"] if not pd.isna(row["Recovery_num"]) else 0
            status = row["PlotStatus"]
            crm = row["CRM"]

            color = OKABE_ITO.get(status, OKABE_ITO["NotEvaluated"])
            marker = crm_marker.get(crm, "o")
            label = crm if crm not in seen_crm_labels else None

            plt.plot([x, x], [0, y], color=color, linewidth=1.2, alpha=0.7)
            plt.scatter(
                x, y,
                color=color,
                s=80,
                marker=marker,
                edgecolor="black",
                linewidth=0.5,
                label=label,
            )

            if label is not None:
                seen_crm_labels.add(label)
            plotted_statuses.add(status)

    plt.axhline(low_tol, color=OKABE_ITO["Line"], linestyle="--", linewidth=1)
    plt.axhline(high_tol, color=OKABE_ITO["Line"], linestyle="--", linewidth=1)

    plt.xticks(list(analyte_positions.values()), analytes, rotation=45, ha="center")
    plt.ylabel("Recovery (%)")
    plt.title("CRM recovery")

    crm_handles = [
        plt.Line2D(
            [0], [0],
            marker=crm_marker.get(crm, "o"),
            linestyle="none",
            color="black",
            markerfacecolor="black",
            label=crm,
        )
        for crm in crm_list
    ]

    status_items = {
        "OK": ("OK", OKABE_ITO["OK"]),
        "Fail": ("Fail", OKABE_ITO["Fail"]),
        "NeedsInvestigation": ("Needs Investigation", OKABE_ITO["NeedsInvestigation"]),
        "NotApplicable": ("Not Applicable", OKABE_ITO["NotApplicable"]),
        "NotEvaluated": ("Not Evaluated", OKABE_ITO["NotEvaluated"]),
        "Line": ("Tolerance", OKABE_ITO["Line"]),
    }

    status_handles = []
    for code, (label, color) in status_items.items():
        if code == "Line" or code in plotted_statuses:
            status_handles.append(
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

    plt.legend(
        handles=crm_handles + status_handles,
        title="CRM materials & status",
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
    )

    plt.tight_layout()
    return plt.gcf()


# ============================================================
# DUPLICATE RPD PLOT  (lollipop — unchanged logic, cleaned up)
# ============================================================
def plot_duplicate_rpd(dup_results, certificate_order, rpd_tolerance=30.0):
    """
    Plot duplicate RPD as a status-coloured lollipop chart.

    Parameters
    ----------
    dup_results : pd.DataFrame
        Output of build_qc_summary() or compute_duplicate_rpd().
    certificate_order : list[str]
        Analyte names in certificate order.
    rpd_tolerance : float
        RPD threshold line drawn on the plot.

    Returns
    -------
    matplotlib.figure.Figure
    """
    df = dup_results.copy()

    df["PlotStatus"] = df["Duplicate_Status"].map(STATUS_MAP).fillna("NotEvaluated")

    df = enforce_certificate_order(
        df,
        certificate_order,
        value_cols=["Duplicate_RPD"],
        status_col="PlotStatus",
    )

    spacing = 1.5
    analytes = df["Analyte"].tolist()
    x_positions_list = [i * spacing for i in range(len(analytes))]

    plt.figure(figsize=(14, 6))
    plotted_statuses = set()

    for i, (_, row) in enumerate(df.iterrows()):
        x = x_positions_list[i]
        y = row["Duplicate_RPD"] if not pd.isna(row["Duplicate_RPD"]) else 0
        status = row["PlotStatus"]
        color = OKABE_ITO.get(status, OKABE_ITO["NotEvaluated"])

        plt.plot([x, x], [0, y], color=color, linewidth=1.2, alpha=0.7)
        plt.scatter(x, y, color=color, s=60, edgecolor="black", linewidth=0.5)
        plotted_statuses.add(status)

    plt.axhline(rpd_tolerance, color=OKABE_ITO["Line"], linestyle="--", linewidth=1)

    plt.xticks(x_positions_list, analytes, rotation=45, ha="center")
    plt.ylabel("RPD (%)")
    plt.title("Duplicate RPD")

    legend_items = {
        "OK":                ("OK",                   OKABE_ITO["OK"]),
        "Fail_RPD":          ("Fail RPD",             OKABE_ITO["Fail_RPD"]),
        "BDL_Substitution":  ("BDL substitution",     OKABE_ITO["BDL_Substitution"]),
        "NeedsInvestigation":("Needs investigation",  OKABE_ITO["NeedsInvestigation"]),
        "NotApplicable":     ("Not applicable",       OKABE_ITO["NotApplicable"]),
        "NotEvaluated":      ("Not evaluated",        OKABE_ITO["NotEvaluated"]),
        "Line":              ("Tolerance",            OKABE_ITO["Line"]),
    }

    handles = []
    for code, (label, color) in legend_items.items():
        if code == "Line" or code in plotted_statuses:
            handles.append(
                plt.Line2D(
                    [0], [0],
                    marker="o" if code != "Line" else None,
                    linestyle="--" if code == "Line" else "none",
                    color=color,
                    markerfacecolor=color if code != "Line" else None,
                    markeredgecolor="black" if code != "Line" else None,
                    markersize=7,
                    label=label,
                )
            )

    plt.legend(handles=handles, title="Duplicate status",
               bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()

    return plt.gcf()


# ============================================================
# BLANK LEVELS PLOT  (lollipop — unchanged logic, cleaned up)
# ============================================================
def plot_blank_levels(blank_results, certificate_order, tolerance_factor=3.0):
    """
    Plot blank levels as a status-coloured lollipop chart.

    Parameters
    ----------
    blank_results : pd.DataFrame
        Output of compute_blank_qc().
    certificate_order : list[str]
        Analyte names in certificate order.
    tolerance_factor : float
        Multiplier applied to DL to draw the exceedance threshold line.

    Returns
    -------
    matplotlib.figure.Figure
    """
    df = blank_results.copy()

    required = ["Analyte", "Average", "DL", "Blank_Status"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        print(f"Missing columns in blank_results: {missing_cols}")
        return None

    df["PlotStatus"] = df["Blank_Status"].map(STATUS_MAP).fillna("NotEvaluated")

    df = enforce_certificate_order(
        df,
        certificate_order,
        value_cols=["Average", "DL"],
        status_col="PlotStatus",
    )

    analytes = df["Analyte"].tolist()
    avg = df["Average"].tolist()
    dl = df["DL"].tolist()
    tolerance = [
        (d * tolerance_factor) if not pd.isna(d) else np.nan for d in dl
    ]

    spacing = 1.5
    x_positions = [i * spacing for i in range(len(analytes))]

    plt.figure(figsize=(14, 6))
    plotted_statuses = set()

    for i, (y, status) in enumerate(zip(avg, df["PlotStatus"])):
        x = x_positions[i]
        color = OKABE_ITO.get(status, OKABE_ITO["NotEvaluated"])
        y_plot = y if not pd.isna(y) else 0

        plt.plot([x, x], [0, y_plot], color=color, linewidth=1.2, alpha=0.7)
        plt.scatter(x, y_plot, color=color, s=60, edgecolor="black", linewidth=0.5)
        plotted_statuses.add(status)

    plt.plot(x_positions, dl,
             color=OKABE_ITO["Line"], linestyle="-", linewidth=1.2, label="DL")
    plt.plot(x_positions, tolerance,
             color=OKABE_ITO["Line"], linestyle="--", linewidth=1.2,
             label=f"Threshold ({tolerance_factor}x DL)")

    plt.xticks(x_positions, analytes, rotation=45, ha="center")
    plt.ylabel("Blank value")
    plt.title("Blank levels")

    legend_items = {
        "OK":                ("OK",                  OKABE_ITO["OK"]),
        "Fail":              ("Fail",                OKABE_ITO["Fail"]),
        "NeedsInvestigation":("Needs investigation", OKABE_ITO["NeedsInvestigation"]),
        "NotApplicable":     ("Not applicable",      OKABE_ITO["NotApplicable"]),
        "NotEvaluated":      ("Not evaluated",       OKABE_ITO["NotEvaluated"]),
        "DL":                ("DL",                  OKABE_ITO["Line"]),
        "Tolerance":         ("Tolerance",           OKABE_ITO["Line"]),
    }

    handles = []
    for code, (label, color) in legend_items.items():
        if code in ["DL", "Tolerance"] or code in plotted_statuses:
            handles.append(
                plt.Line2D(
                    [0], [0],
                    marker="o" if code not in ["DL", "Tolerance"] else None,
                    linestyle="-" if code == "DL" else "--" if code == "Tolerance" else "none",
                    color=color,
                    markerfacecolor=color if code not in ["DL", "Tolerance"] else None,
                    markeredgecolor="black" if code not in ["DL", "Tolerance"] else None,
                    markersize=7,
                    label=label,
                )
            )

    plt.legend(handles=handles, title="Blank status",
               bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()

    return plt.gcf()