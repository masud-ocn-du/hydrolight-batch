"""
STEP 4: Isolated Worker Sandboxes & Fortran Scratch-File Scrubbing
------------------------------------------------------------------
HydroLight6.exe writes unbuffered Fortran scratch files (fort.*, temp.*, *.dis)
into its current working directory. Running multiple workers inside a single
C:\HE60\backend folder causes file-lock collisions and periodic worker crashes.

This module:
  1. Clones C:\HE60\backend into isolated directories (backend_w1 .. backend_wN).
  2. Scrubs generic Fortran scratch files before and after every simulation run.
  3. Cleans up intermediate per-run output files (I*, M*, D*, P*, L*, H*, S*)
     once the spectrum has been parsed and saved to CSV.
"""

import glob
import os
import shutil
from .config import SimulationConfig

SCRATCH_PATTERNS = ["fort.*", "temp.*", "*.dis", "*.tmp", "scratch.*", "hhl.dat"]


def initialize_worker_sandboxes(config: SimulationConfig) -> None:
    """
    Clones the master HydroLight backend folder into `max_workers` isolated
    sandbox directories (`backend_w1` .. `backend_wN`).
    """
    if not os.path.exists(config.backend_dir):
        raise FileNotFoundError(
            f"Master HydroLight backend folder not found at: '{config.backend_dir}'"
        )

    for worker_id in range(1, config.max_workers + 1):
        sandbox = config.sandbox_dir(worker_id)
        shutil.copytree(config.backend_dir, sandbox, dirs_exist_ok=True)


def clean_sandbox_scratch_files(sandbox_dir: str) -> None:
    """
    Deletes generic Fortran scratch files inside a worker sandbox before and
    after each HydroLight6.exe execution.
    """
    if not os.path.exists(sandbox_dir):
        return

    for pattern in SCRATCH_PATTERNS:
        for filepath in glob.glob(os.path.join(sandbox_dir, pattern)):
            try:
                os.remove(filepath)
            except OSError:
                pass


def cleanup_all_run_files(root_name: str, config: SimulationConfig) -> None:
    """
    Removes temporary intermediate input/output files for a completed simulation
    (`I<root>.*`, `M<root>.*`, `D<root>.*`, `P<root>.*`, `L<root>.*`, `H<root>.*`,
    `S<root>.*`) so disk usage remains small during multi-thousand-run batches.
    """
    prefixes = ["I", "M", "D", "P", "L", "H", "S", ""]
    extensions = ["*.txt", "*.dat", "*.csv", "*.xlsx", "*.xls", "*.log", "*.dis"]

    sandbox_dirs = [config.sandbox_dir(i) for i in range(1, config.max_workers + 1)]
    target_dirs = list(set([config.batch_dir, config.backend_dir] + config.output_search_dirs + sandbox_dirs))
    protected_csv = os.path.abspath(config.output_csv)

    for directory in target_dirs:
        if not os.path.exists(directory):
            continue
        for prefix in prefixes:
            for ext in extensions:
                pattern = os.path.join(directory, f"{prefix}{root_name}{ext}")
                for filepath in glob.glob(pattern):
                    if os.path.abspath(filepath) == protected_csv:
                        continue
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
