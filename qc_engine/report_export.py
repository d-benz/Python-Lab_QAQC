import os
from datetime import datetime

def save_qc_plot(
    fig,
    lab_name,
    metadata_name,
    report_date,
    plot_type,
    outdir="output"
):
    """
    Save a QC plot with a standardized footer.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        The figure to save.
    lab_name : str
        Laboratory or organization name.
    metadata_name : str
        Certificate or metadata identifier.
    report_date : str or datetime
        Report date to include in footer.
    plot_type : str
        Type of QC plot (e.g., 'CRM Recovery').
    outdir : str
        Output directory for saved images.
    """

    if fig is None:
        return

    # Build footer components
    footer_parts = [
        lab_name,
        f"Certificate: {metadata_name}",
    ]

    if report_date:
        footer_parts.append(f"Report Date: {report_date}")

    footer_text = " | ".join(footer_parts)

    # Add footer below the plot
    fig.text(
        0.5,
        -0.05,
        footer_text,
        ha="center",
        fontsize=10
    )

    # Ensure output directory exists
    os.makedirs(outdir, exist_ok=True)

    # Build filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_plot_type = plot_type.replace(" ", "_")
    fname = f"{outdir}/{safe_plot_type}_{metadata_name}_{timestamp}.png"

    fig.savefig(fname, dpi=300, bbox_inches="tight")
    print(f"Saved: {fname}")