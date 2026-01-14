# Laboratory QC Interpretation Toolkit

This coding companion provides a transparent, reproducible, and scientifically grounded workflow for evaluating **internal laboratory quality‑control (QC)** data included in geochemical assay certificates. The toolkit processes the QC inserted by the laboratory itself – Certified Reference Materials (CRMs), pulp duplicates, and method blanks – to produce a unified QC summary and a short, descriptive narrative to help users understand laboratory QC behaviour.

Internal lab QC is essential for assessing the reliability of assay results, yet it is often reviewed only visually or manually in the form of CRM recovery tables, duplicate RPD calculations, and blank exceedance checks. Many reviewers rely on ad hoc Excel formulas or custom spreadsheets, which can be inconsistent, tedious to reproduce, and prone to errors. Some commercial geochemistry platforms include high‑level QC dashboards that are typically focused on client‑inserted QC (such as field duplicates, coarse rejects, and standards) or general data visualization. 

This coding companion evaluates **one QC spreadsheet at a time**, reflecting the structure of most assay certificates. It is well suited to small exploration programs, early‑stage projects, and educational use where explorers want to learn how to interpret laboratory QC more consistently. The `interpretation.py` module generates a concise, descriptive narrative to support internal documentation and learning.

This workflow does **not** replace internal laboratory QA/QC validation procedures, professional judgement, or Qualified Person (QP) oversight. The narrative output is **educational**, **descriptive**, and **non‑prescriptive**. Users remain responsible for all technical interpretations, conlusions, and decisions.

---

## Why this toolkit matters

- **Transparent, reproducible QC evaluation**  
- **Educational focus** to help explorers learn how to interpret internal lab QC  
- **Matrix‑aware** and **method‑aware** generalized descriptions  
- **Unified QC summary** table plus a short narrative explanation  
- **Consistent internal reporting** and documentation  

---

## What this toolkit does

- **Evaluates CRM recoveries** using:
  - Recovery %
  - Bias %
  - User‑defined CRM tolerance thresholds

- **Computes duplicate precision** using Relative Percent Difference (RPD)
  - User‑defined RPD tolerance
  - Handling of `<DL` values and precision context

- **Assesses blank contamination** using:
  - Mean
  - Standard deviation
  - User‑defined blank exceedance factor (e.g., 3× DL)
  - User‑defined BDL substitution rule (e.g., DL/2, DL/√2, 0, DL, or a numeric value)

- **Produces a unified QC summary table**

- **Generates a short, descriptive narrative** including:
  - Total sample, CRM, duplicate pairs, and blank counts
  - CRM performance
  - Duplicate precision
  - Blank behaviour
  - Digestion‑method context
  - Matrix‑specific context
  - The QC tolerances and BDL substitution rule applied

- **Extracts metadata**:
  - File name
  - Report number
  - Report date  

- **Provides QC plots tracking Pass, Fails, and Not Applicable**

---

## What this toolkit does *not* do

- Replace laboratory QA/QC verification procedures  
- Certify assay accuracy  
- Diagnose root causes of QC failures  
- Provide regulatory or reporting compliance  
- Interpret geological or grade results  
- Replace the judgement of a Qualified Person (QP)  

**Professional judgement remains essential.**

---

# QC calculations used in this toolkit

### CRM Recovery %

Recovery % = (Measured Value / Certified Value) × 100

### CRM Bias %

Bias % = ((Measured Value – Certified Value) / Certified Value) × 100

### Duplicate Relative Percent Difference (RPD)

RPD % = |Sample1 – Sample2| / ((Sample1 + Sample2) / 2) × 100

### Blank Mean

Blank Mean = Σ(blank values) / n

### Blank Standard Deviation

Blank SD = sqrt( Σ(x – mean)² / (n – 1) )

### BDL Substitution

Values reported as `<DL` are replaced using a **user‑defined substitution rule**, for example:

- `"half"` → DL/2  
- `"sqrt2"` → DL/√2  
- `"zero"` → 0  
- `"dl"` → DL  
- A numeric value → fixed substitution  

---

# Pass/fail thresholds

Thresholds for CRM recovery, duplicate RPD, blank exceedances, and BDL substitution are controlled by user‑defined settings in the main notebook, for example:

- `crm_low_tol`, `crm_high_tol` <-- CRM tolerances
- `duplicate_rpd_tol` <-- Duplicate Relative Percent Difference tolerance
- `blank_tol_factor` <-- Blank tolerance factor
- `bdl_sub_rule` <-- Blank Below Detection Limit substitution

These values are passed into the QC engine and the interpretation module, allowing users to adjust QC criteria to match project‑specific or laboratory‑specific requirements.

---

# Project structure

| File / Module             | Purpose                                                |
|---------------------------|--------------------------------------------------------|
| `01_QC_Interpreter.ipynb` | Single coding companion (main user‑facing notebook)   |
| `blank_wide.py`           | Blank evaluation logic + BDL substitution handling    |
| `classifier.py`           | QC classification utilities                            |
| `column_namer.py`         | Standardized column naming                             |
| `crm_wide.py`             | CRM evaluation logic                                   |
| `duplicate_wide.py`       | Duplicate evaluation logic                             |
| `interpretation.py`       | Narrative QC interpretation engine                     |
| `parser.py`               | Input parsing and preprocessing                        |
| `qc_plots.py`             | Optional QC visualization tools                        |
| `qc_summary.py`           | Unified QC summary builder                             |
| `report_export.py`        | Export utilities for summaries and interpretations     |
| `report_metadata.py`      | File name and metadata extraction                      |

---

# Required Python packages

This toolkit uses the following Python packages, each protected under its own license:

- **sys** — Standard Python library  
- **os** — Standard Python library  
- **pandas** — https://pandas.pydata.org  
- **numpy** — https://numpy.org  
- **re** — Standard Python library  
- **matplotlib** — https://matplotlib.org  
- **datetime** — Standard Python library  

Users should review each package’s license prior to use.

---

# Getting started

## 1. Open the notebook

`01_QC_Interpreter.ipynb`

## 2. Update the user inputs

- `path = "path/to/your/file.xlsx"`
- `lab_name = "Labratory Name"`
- `meta_key = "Report Number"`
- `date_key = "Report Date"`

- `method_code = "Lab Method Code"`      # Choose from printed list  
- `matrix_type = "Sample Material"`        # Choose from printed list  

The notebook prints available `method_code` and `matrix_type` options for convenience.

### QC tolerance and BDL default settings

- `crm_low_tol = 80.0`          # CRM lower recovery tolerance (%)  
- `crm_high_tol = 120.0`        # CRM upper recovery tolerance (%)  
- `duplicate_rpd_tol = 30.0`    # Duplicate RPD tolerance (%)  
- `blank_tol_factor = 3.0`      # Blank exceedance factor (e.g., 3× DL)  
- `bdl_sub_rule = "half"`       # BDL substitution rule: "half", "sqrt2", "zero", "dl", or numeric  

## 3. Run the workflow

The notebook will:

- Parse metadata  
- Describe common CRMs, duplicates, and blanks behaviours and devaiations
- Apply user‑defined tolerances and BDL substitution rule  
- Build a QC summary  
- Generate the descriptive narrative  
- Save QC plots to an output folder as `.png` files  

## Output

- QC summary tables (not exported)  
- Short descriptive QC narrative (not exported)
- CRM Recovery, Duplicate RPD, and blank QC plots (saved to a output folder)

These outputs support internal QA/QC review and help explorers learn how to interpret laboratory QC.

---

# Future improvements

- Batch evaluation of multiple QC spreadsheets  
- Expanded digestion‑method libraries  
- Batch‑level QC statistics  
- Multi‑lab dataset support  

---

