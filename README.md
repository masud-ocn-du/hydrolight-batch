# hydrolight-batch

**Template-Driven Parallel HydroLight 6.0 Batch Runner & Output Post-Processor (`v1.0.0`)**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![ORCID](https://img.shields.io/badge/ORCID-0000--0003--3036--8167-green.svg)](https://orcid.org/0000-0003-3036-8167)

---

> ### Important Notice & Software Prerequisite
> **`hydrolight-batch` is NOT the HydroLight 6.0 radiative transfer software itself.**
>
> * This package is an open-source Python automation wrapper that executes **HydroLight 6.0** in parallel batches and post-processes its output files (`M***.txt`) into analysis-ready CSV datasets.
> * This repository does **not** include `HydroLight6.exe`, proprietary lookup tables, or any licensed components of HydroLight/EcoLight.
> * **User License Required:** To execute simulations (`hydrolight-batch run`), you **must already have a valid, licensed installation of HydroLight 6.0 for Windows** (typically installed at `C:\HE60\backend\HydroLight6.exe`) on your computer.
> * **Platform Note:** Template inspection (`hydrolight-batch inspect-template`) runs on **Windows, macOS, and Linux**, whereas batch simulation execution (`hydrolight-batch run`) requires **Windows** with HydroLight 6.0 installed.

---

## Overview

`hydrolight-batch` automates large-scale radiative transfer dataset generation using your existing **HydroLight 6.0** installation. Instead of manually configuring and running single water-column cases one by one through the HydroLight GUI, `hydrolight-batch`:

1. **Inspects any HydroLight input template (`I***.txt`):** Dynamically reads optical component counts, spectral band counts, wavelength edges, and sensor classification (`hyperspectral` vs. `multispectral`) from templates such as `ISAB.txt` or `ISAB2.txt`.
2. **Generates bio-optical parameter manifests:** Samples Chlorophyll-a (`Chla`), colored dissolved organic matter (`CDOM`), and `Minerals/TSS` across log-uniform distributions (and mineral backscattering ratio $b_b/b$ uniformly) to cover oligotrophic to hyper-turbid aquatic regimes.
3. **Runs `HydroLight6.exe` in parallel across isolated sandboxes:** Clones `C:\HE60\backend` into isolated worker directories (`backend_w1` ... `backend_wN`) and scrubs temporary Fortran scratch files (`fort.*`, `temp.*`, `*.dis`, etc.) before and after each simulation to prevent file-lock collisions.
4. **Post-processes outputs to CSV:** Parses native remote sensing reflectance $R_{rs}(\lambda)$ across every template band, total backscattering $b_b(550\text{ nm})$, and input IOP concentrations directly into a clean CSV file—with Excel file-lock retry protection and `--resume` recovery for interrupted runs.

---

## Prerequisites

1. **Licensed HydroLight 6.0 (Windows):** Installed locally (default root `C:\HE60` containing `backend\HydroLight6.exe`, `run\`, and `output\`), plus a valid GUI-generated HydroLight input template (`I***.txt`).
2. **Python ($\ge 3.9$):** Recommended via [Anaconda](https://www.anaconda.com/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) with `numpy` and `pandas`.
3. **Local SSD Storage:** Store `C:\HE60` and your output workspace on an internal drive outside cloud-synced folders (OneDrive, Dropbox, Google Drive) so background sync services do not lock Fortran scratch files mid-run.

---

## Installation & Verification

### 1. Create a Python Environment and Install

```bash
# Create and activate a dedicated Conda environment
conda create -n hydrolight python=3.11 numpy pandas -y
conda activate hydrolight

# Install directly from GitHub
pip install git+https://github.com/masud-ocn-du/hydrolight-batch.git
```

*(Alternatively, if you cloned or downloaded this repository locally, run `pip install -e .` from inside the repository root.)*

### 2. Verify Installation

```bash
# 1. Confirm package version and metadata
pip show hydrolight-batch

# 2. Confirm CLI commands are available
hydrolight-batch --help

# 3. Inspect a HydroLight input template (works on Windows, macOS, and Linux)
hydrolight-batch inspect-template --template examples/ISAB.txt
```

---

## Quick Start

### 1. Inspect Your HydroLight Input Template

Before running a batch, verify how `hydrolight-batch` parses your `I***.txt` file:

```bash
hydrolight-batch inspect-template --template C:\HE60\run\ISAB.txt
```

### 2. Run a Default 5-Simulation Verification Batch (Windows)

By default, `hydrolight-batch run` executes **5 simulations** (`--n-runs 5`) so you can verify end-to-end execution with your local `HydroLight6.exe` installation in seconds:

```bash
hydrolight-batch run --template C:\HE60\run\ISAB.txt --output Test_5Runs.csv
```

### 3. Scale Up to Full Parallel Production Runs (Windows)

Assign CPU cores via `--workers` (leave 1–2 physical cores free for the OS) and customize bio-optical concentration bounds:

```bash
hydrolight-batch run ^
  --he60-dir C:\HE60 ^
  --template C:\HE60\run\ISAB.txt ^
  --n-runs 5000 ^
  --workers 6 ^
  --timeout 900 ^
  --chl-min 0.05 --chl-max 35.0 ^
  --cdom-min 0.01 --cdom-max 1.5 ^
  --minerals-min 0.5 --minerals-max 250.0 ^
  --bb-ratio-min 0.008 --bb-ratio-max 0.040 ^
  --seed 2026 ^
  --output Coastal_Estuarine_Rrs_Dataset.csv
```

### 4. Resume an Interrupted Batch

If a large multi-hour batch is interrupted, pass `--resume` with the same `--output` path and `--seed` to execute only the remaining missing `RunID` cases:

```bash
hydrolight-batch run --template C:\HE60\run\ISAB.txt --n-runs 5000 --workers 6 --seed 2026 --resume --output Coastal_Estuarine_Rrs_Dataset.csv
```

---

## Python API Usage

```python
from hydrolight_batch import SimulationConfig, BatchRunner, inspect_template

# 1. Inspect template structure
meta = inspect_template(r"C:\HE60\run\ISAB.txt")
print(f"Detected {meta.sensor_type} template with {meta.n_bands} bands ({meta.wl_min}-{meta.wl_max} nm)")

# 2. Configure and run parallel batch
config = SimulationConfig(
    he60_dir=r"C:\HE60",
    template_file=r"C:\HE60\run\ISAB.txt",
    output_csv="HydroLight_Rrs_bb_Dataset.csv",
    n_runs=500,
    max_workers=6,
    seed=101,
)

runner = BatchRunner(config)
runner.run()
```

---

## Output Dataset Format

Each completed simulation appends one row to the target CSV file:

| Column | Units | Description |
| :--- | :--- | :--- |
| `RunID` | — | Unique simulation identifier (e.g., `SAB_0001`) |
| `Chla_mg_m3` | $\text{mg m}^{-3}$ | Sampled Chlorophyll-a concentration (log-uniform) |
| `CDOM_m1` | $\text{m}^{-1}$ | Sampled CDOM absorption coefficient at $440\text{ nm}$ (log-uniform) |
| `Minerals_mg_L` | $\text{mg L}^{-1}$ | Sampled mineral / TSS concentration (log-uniform) |
| `bb_ratio_input` | Unitless | Sampled mineral particle backscattering ratio $b_b/b$ (uniform) |
| `bb_total_550nm` | $\text{m}^{-1}$ | Total backscattering coefficient $b_b$ at $550\text{ nm}$ (full spectrum optional via `--include-full-bb`) |
| `Rrs_<wl>nm` | $\text{sr}^{-1}$ | Native remote sensing reflectance $R_{rs}(\lambda)$ across every band in the input template |

---

## Documentation & Examples

* **Beginner & Technical User Guide (PDF):** See [`docs/hydrolight_batch_user_guide.pdf`](docs/hydrolight_batch_user_guide.pdf) for step-by-step installation checks, CPU core sizing guidelines, runtime flags, and bio-optical sampling equations.
* **Sample Input Template:** See [`examples/ISAB.txt`](examples/ISAB.txt) for a 5-component, 165-band ($396\text{–}724\text{ nm}$) template ready for testing `inspect-template`.

---

## Author, Citation & License

* **Author:** Md Masud-Ul-Alam ([ORCID: 0000-0003-3036-8167](https://orcid.org/0000-0003-3036-8167))
* **Affiliation:** Skidaway Institute of Oceanography, University of Georgia (UGA)
* **License:** Released under the [MIT License](LICENSE).

If you use or adapt `hydrolight-batch` in research datasets or publications, please cite this software (see [`CITATION.cff`](CITATION.cff)):

> Masud-Ul-Alam, Md & Rivero-Calle, Sara (2026). *hydrolight-batch: Template-Driven Parallel HydroLight 6.0 Simulation Pipeline (v1.0.0)*. Skidaway Institute of Oceanography, University of Georgia. https://github.com/masud-ocn-du/hydrolight-batch