"""
STEP 3: Bio-Optical Parameter Manifest Generator
------------------------------------------------
Generates reproducible, unbiased synthetic water-column constituent combinations
using Log-Uniform sampling for Chla, CDOM, and Minerals (TSS), and Uniform
sampling for the mineral particle backscattering ratio (bb/b).
"""

from typing import Any, Dict, List
import numpy as np
from .config import ParameterBounds


def generate_parameter_manifest(
    n_runs: int = 5,
    bounds: ParameterBounds = ParameterBounds(),
    seed: int = 101,
    run_prefix: str = "SAB",
) -> List[Dict[str, Any]]:
    """
    Builds a deterministic list of `n_runs` simulation parameter dictionaries.

    Parameters
    ----------
    n_runs : int
        Number of radiative transfer simulations to generate (default: 5).
    bounds : ParameterBounds
        Min/max sampling limits for Chla, CDOM, Minerals (TSS), and bb/b ratio.
    seed : int
        NumPy random seed for reproducible dataset generation.
    run_prefix : str
        Short prefix (<= 4 chars) for RunIDs (e.g., 'SAB' -> 'SAB_0001').
    """
    rng = np.random.default_rng(seed)

    chl_array = np.exp(rng.uniform(np.log(bounds.chl_min), np.log(bounds.chl_max), n_runs))
    cdom_array = np.exp(rng.uniform(np.log(bounds.cdom_min), np.log(bounds.cdom_max), n_runs))
    minerals_array = np.exp(rng.uniform(np.log(bounds.minerals_min), np.log(bounds.minerals_max), n_runs))
    bb_ratio_array = rng.uniform(bounds.bb_ratio_min, bounds.bb_ratio_max, n_runs)

    pad_width = max(4, len(str(n_runs)))
    params_list: List[Dict[str, Any]] = []

    for i in range(n_runs):
        run_id = f"{i + 1:0{pad_width}d}"
        root_name = f"{run_prefix}_{run_id}"
        params_list.append({
            "run_index": i + 1,
            "run_id": run_id,
            "root_name": root_name,
            "chl": float(chl_array[i]),
            "cdom": float(cdom_array[i]),
            "minerals": float(minerals_array[i]),
            "bb_ratio": float(bb_ratio_array[i]),
        })

    return params_list
