# hydrolight-batch

A modular, template-driven Python package for running parallel **HydroLight 6.0** radiative transfer simulations and exporting ML-ready CSV datasets containing full-range $R_{rs}(\lambda)$ spectra alongside constituent concentrations (`Chla`, `CDOM`, `Minerals/TSS`, and total backscattering $b_b$).

**Author:** Md Masud-Ul-Alam ([ORCID: 0000-0003-3036-8167](https://orcid.org/0000-0003-3036-8167))  
**Affiliation:** UGA Skidaway Institute of Oceanography  
**Repository:** [https://github.com/masud-ocn-du/hydrolight-batch](https://github.com/masud-ocn-du/hydrolight-batch)

---

## Key Capabilities

1. **Dynamic `I***.txt` Template Inspection (`template.py`)**:
   - Automatically parses any user-supplied HydroLight input template (`ISAB.txt`, `ISAB2.txt`, `Itest.txt`, etc.).
   - Detects the number of optical components (`ncomp`), total spectral bands (`n_bands`), band boundary edges, band center wavelengths, and automatically classifies the run as **`hyperspectral`** or **`multispectral`**.
   - Injects sampled concentrations (`Chla`, `CDOM`, `Minerals/TSS`) and mineral backscattering ratios ($b_b/b$) into the exact component lines regardless of whether the template has 4, 5, or more components.
2. **Full-Range Native $R_{rs}$ & IOP Export (`parser.py`, `runner.py`)**:
   - Extracts the complete simulated $R_{rs}(\lambda)$ spectrum across every band defined in your `I***.txt` file (`Rrs_<wl>nm`), together with `RunID`, `Chla_mg_m3`, `CDOM_m1`, `Minerals_mg_L` (TSS), `bb_ratio_input`, and `bb_total_550nm` (plus optional full-spectrum `bb_<wl>nm` columns).
3. **Parallel Sandboxed Execution (`sandbox.py`, `runner.py`)**:
   - Clones `C:\HE60\backend` into isolated worker folders (`backend_w1` .. `backend_wN`) and scrubs generic Fortran scratch files (`fort.*`, `temp.*`, `*.dis`, `*.tmp`) before and after every simulation to eliminate multi-worker file collisions.
4. **Configurable Simulation Count (`n_runs = 5` Default) & Resume Support**:
   - Defaults to **`n_runs = 5`** so new users can verify their setup immediately in seconds, and scales effortlessly to any desired batch size (`500`, `5000`, `8000`, etc.) by changing a single parameter (`n_runs` or `--n-runs`).

---

## Quick Start (Beginner to End)

### Step 1: Install the Package
Run the one-step installer script (`python install_hydrolight_batch.py`) or open PowerShell inside `hydrolight_batch_package` and run:

```powershell
pip install -e .
```

### Step 2: Inspect Your `I***.txt` Template File
Navigate to your working folder (e.g., `C:\HE60\work`) where your HydroLight template file (`ISAB.txt`, `ISAB2.txt`, etc.) is located and inspect it:

```powershell
hydrolight-batch inspect-template --template ISAB.txt
```

### Step 3: Run a Batch Simulation (Default: 5 Simulations)
By default, `hydrolight-batch` runs **5 simulations** (`--n-runs 5`) so you can verify everything quickly. To generate a larger dataset, simply change `--n-runs` (e.g., `--n-runs 5000` or `--n-runs 8000`):

```powershell
# Default quick test (5 simulations):
hydrolight-batch run --template ISAB.txt --output HydroLight_Rrs_bb_Dataset.csv

# Scale up to any desired number of simulations (e.g., 8,000 runs across 8 workers):
hydrolight-batch run --template ISAB.txt --n-runs 8000 --workers 8 --timeout 900 --output HydroLight_Rrs_bb_Dataset.csv
```

Or run via Python script (see `examples/run_batch_from_template.py`):

```python
from hydrolight_batch import BatchRunner, ParameterBounds, SimulationConfig

config = SimulationConfig(
    n_runs=5,                   # Default is 5; change to any target number (e.g., 500, 5000, 8000)
    max_workers=8,
    timeout_seconds=900,
    seed=101,
    he60_dir=r"C:\HE60",
    template_file="ISAB.txt",
    output_csv="HydroLight_Rrs_bb_Dataset.csv",
    resume=False,
    bounds=ParameterBounds(
        chl_min=0.001,
        chl_max=50.0,
        cdom_min=0.003,
        cdom_max=0.8,
        minerals_min=1.0,
        minerals_max=1000.0,
        bb_ratio_min=0.005,
        bb_ratio_max=0.050,
    ),
)

BatchRunner(config).run()
```

---

## License & Citation

This software is released under the **MIT License** (see `LICENSE`). You are free to use, modify, and distribute this package for academic or commercial purposes, provided that you retain the copyright notice and cite the author:

```bibtex
@software{masud_ul_alam_hydrolight_batch_2026,
  author       = {Masud-Ul-Alam, Md},
  title        = {hydrolight-batch: Template-Driven Parallel HydroLight 6.0 Simulation Pipeline},
  year         = {2026},
  version      = {1.0.0},
  institution  = {UGA Skidaway Institute of Oceanography},
  orcid        = {https://orcid.org/0000-0003-3036-8167},
  url          = {https://github.com/masud-ocn-du/hydrolight-batch}
}
```
