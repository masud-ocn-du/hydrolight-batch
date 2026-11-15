"""
STEP 1: Configuration Dataclasses
---------------------------------
Defines all configurable parameters for HydroLight directory paths, parallel worker
counts, constituent sampling bounds, and component index mapping inside I***.txt.
"""

from dataclasses import dataclass, field
import os
from typing import List


@dataclass
class ParameterBounds:
    """
    Bio-optical constituent sampling bounds for synthetic dataset generation.

    - Chla, CDOM, and Minerals (TSS) are sampled using Log-Uniform distributions
      so low and high concentration regimes are represented evenly across orders
      of magnitude.
    - bb_ratio (backscattering-to-scattering ratio bb/b for mineral particles)
      is sampled using a Uniform distribution.
    """
    chl_min: float = 0.001        # Chlorophyll-a minimum (mg/m^3)
    chl_max: float = 50.0         # Chlorophyll-a maximum (mg/m^3)
    cdom_min: float = 0.003       # CDOM absorption a_cdom(440) minimum (m^-1)
    cdom_max: float = 0.8         # CDOM absorption a_cdom(440) maximum (m^-1)
    minerals_min: float = 1.0     # Minerals / TSS minimum (mg/L)
    minerals_max: float = 1000.0  # Minerals / TSS maximum (mg/L)
    bb_ratio_min: float = 0.005   # Mineral particle bb/b ratio minimum (unitless)
    bb_ratio_max: float = 0.050   # Mineral particle bb/b ratio maximum (unitless)


@dataclass
class SimulationConfig:
    """
    Master runtime configuration for a parallel HydroLight 6.0 batch.

    Change `n_runs` to generate any desired number of simulations (default: 5).
    """
    # Batch size (default = 5 for quick verification; change to e.g. 500, 5000, 8000)
    n_runs: int = 5
    max_workers: int = 8
    timeout_seconds: int = 900
    seed: int = 101

    # HydroLight installation root and template/output filenames
    he60_dir: str = r"C:\HE60"
    template_file: str = "ISAB.txt"
    output_csv: str = "HydroLight_Rrs_bb_Dataset.csv"

    # RunID prefix (must be <= 4 chars so '<prefix>_0001' fits HydroLight's 8-char limit)
    run_prefix: str = "SAB"

    # 0-based component slot indices inside the I***.txt concentration record (Record 5b):
    # Standard HydroLight 4- or 5-component Case-2 setup:
    #   slot 0 = pure water (kept unchanged)
    #   slot 1 = Chlorophyll-a
    #   slot 2 = CDOM
    #   slot 3 = Minerals / TSS
    chl_component_idx: int = 1
    cdom_component_idx: int = 2
    minerals_component_idx: int = 3

    # Optional: also export full-spectrum bb_<wl>nm columns in addition to bb_total_550nm
    include_full_bb_spectrum: bool = False

    # Optional resume flag:
    #   False -> Overwrite output_csv and start from Run 1
    #   True  -> Keep existing rows in output_csv and run only missing RunIDs
    resume: bool = False

    # Small worker launch stagger (seconds) to smooth initial disk I/O bursts
    stagger_seconds: float = 0.10

    # Constituent sampling bounds
    bounds: ParameterBounds = field(default_factory=ParameterBounds)

    @property
    def backend_dir(self) -> str:
        """Path to the master HydroLight backend folder containing HydroLight6.exe."""
        return os.path.join(self.he60_dir, "backend")

    @property
    def batch_dir(self) -> str:
        """Path where per-run input files (I<root>.txt) are written."""
        return os.path.join(self.he60_dir, "run", "batch")

    @property
    def output_search_dirs(self) -> List[str]:
        """Candidate directories where HydroLight writes M<root>.txt output files."""
        return [
            os.path.join(self.he60_dir, "output", "HydroLight"),
            os.path.join(self.he60_dir, "output", "HydroLight", "excel"),
            os.path.join(self.he60_dir, "output", "HydroLight", "digital"),
            os.path.join(self.he60_dir, "output", "HydroLight", "printout"),
            os.path.join(self.he60_dir, "output"),
            self.backend_dir,
        ]

    def sandbox_dir(self, worker_id: int) -> str:
        """Path to an isolated worker directory (e.g., C:\HE60\backend_w1)."""
        return os.path.join(self.he60_dir, f"backend_w{worker_id}")
