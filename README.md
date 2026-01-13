# Laboratory QC Interpretation Toolkit

This coding companion provides a transparent, reproducible, and scientifically grounded workflow for evaluating **internal laboratory quality‑control (QC)** data included in geochemical assay certificates. The toolkit processes the QC inserted by the laboratory itself - Certified Reference Materials (CRMs), pulp duplicates, and method blanks - to produce a unified QC summary and a short, descriptive narrative to help users understand laboratory QC behaviour.

Internal lab QC is essential for assessing the reliability of assay results, yet it is often just reviewed visually  or manually in the form of CRM recovery tables, duplicate RPD calculations, and blank exceedance checks. Many reviewers rely on ad hoc Excel formulas or custom spreadsheets, which can be inconsistent, tedious to reproduce, and prone to errors. Some commercial geochemistry platforms include high‑level QC dashboards that are typically focused on client‑inserted QC (such as field duplicates, coarse rejects, and standards) or general data visualization. 

This coding companion evaluates **one QC spreadsheet at a time**, reflecting the structure of most assay certificates. It is well suited to small exploration programs, early‑stage projects, and educational use where explorers want to learn how to interpret laboratory QC more consistently. The `interpretation.py` module generates a concise, descriptive narrative to support internal documentation and learning.

This workflow does **not** replace laboratory QA/QC procedures, professional judgement, or Qualified Person (QP) oversight. The narrative output is **educational**, **descriptive**, and **non‑prescriptive**. Users remain responsible for all technical interpretations and decisions.

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
  - Within thresholds and < DL bias

- **Computes duplicate precision** using Relative Percent Difference (RPD)
  - Within thresholds and < DL bias 

- **Assesses blank contamination** using:
  - Mean
  - Standard deviation
  - Within thresholds and < DL bias  

- **Produces a unified QC summary table**

- **Generates a short, descriptive narrative** including:
  - Total sample, CRM, duplicate pairs, and blank counts
  - CRM performance
  - Duplicate precision
  - Blank behaviour
  - Digestion‑method context
  - Matrix‑specific context  

- **Extracts metadata**:
  - File name
  - Report number
  - Report date  

- **Provides QC plots tracking Pass, Fails, and Not Applicable**

---

## What this toolkit does *not* do

- Replace laboratory QA/QC procedures  
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

---

# Pass/fail thresholds
Thresholds for CRM recovery, duplicate RPD, and blank exceedances can be modified directly in:
- crm_wide.py
- duplicate_wide.py
- blank_wide.py
This allows users to adjust QC criteria to match project‑specific or laboratory‑specific requirements.

---

# Project structure

| File / Module            | Purpose                                                |
|--------------------------|--------------------------------------------------------|
| `01_QC_Interpreter.ipynb` | Single coding companion (main user-facing notebook)   |
| `blank_wide.py`          | Blank evaluation logic                                 |
| `classifier.py`          | QC classification utilities                            |
| `column_namer.py`        | Standardized column naming                             |
| `crm_wide.py`            | CRM evaluation logic                                   |
| `duplicate_wide.py`      | Duplicate evaluation logic                             |
| `interpretation.py`      | Narrative QC interpretation engine                     |
| `parser.py`              | Input parsing and preprocessing                        |
| `qc_plots.py`            | Optional QC visualization tools                        |
| `qc_summary.py`          | Unified QC summary builder                             |
| `report_export.py`       | Export utilities for summaries and interpretations     |
| `report_metadata.py`     | File name and metadata extraction                      |

---

# Required Python packages
This toolkit uses the following Python packages, each protected under its own license:
- sys — Standard Python library
- os — Standard Python library
- pandas — https://pandas.pydata.org
- numpy — https://numpy.org
- re — Standard Python library
- matplotlib — https://matplotlib.org
- datetime — Standard Python library
Users should review each package’s license prior to use.

---

# Getting started
## 1. Open the notebook

'01_QC_Interpreter.ipynb'


## 2. Update the user inputs
- path = "path/to/your/file.xlsx"
- lab_name = "Actlabs"
- meta_key = "Report Number"
- date_key = "Report Date"

- method_code = "FA-ICP"      # Choose from printed list
- matrix_type = "soil"        # Choose from printed list

The notebook prints valid method_code and matrix_type options for convenience.

## 3. Run the workflow
The notebook will:
- Parse metadata
- Evaluate CRMs, duplicates, and blanks
- Build the QC summary
- Generate the descriptive narrative
- Save QC plots to an output folder as a .png file

## Output
- QC summary table
- Short descriptive QC narrative
- CRM Recovery, Duplicate RPD, and CRM Recovery QC plots
  
These outputs support internal QA/QC review and help explorers learn how to interpret laboratory QC.

---

# Future improvements
- Batch evaluation of multiple QC spreadsheets
- Expanded digestion‑method libraries
- Batch‑level QC statistics
- Multi‑lab dataset support
- Enhanced visualization modules
- Additional matrix‑aware interpretation rules

---
