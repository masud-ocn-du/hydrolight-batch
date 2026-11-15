"""
STEP 5: HydroLight M***.txt Output Locator & Full-Range Rrs / bb Parser
-----------------------------------------------------------------------
Locates the multi-sheet ASCII output file (M<root_name>.txt) produced by
HydroLight 6.0 and parses:
  - Every simulated wavelength (nm) across the template's full spectral range
  - Remote Sensing Reflectance Rrs(lambda) (1/sr) for all bands
  - Total backscattering coefficient bb (1/m) at 550 nm (or nearest simulated band)
    and optionally across the full simulated wavelength grid
"""

import glob
import os
from typing import Dict, List, Optional, Tuple
import numpy as np
from .config import SimulationConfig


def format_wavelength_col(wavelength_nm: float, prefix: str = "Rrs") -> str:
    """
    Formats a wavelength into a clean CSV column name:
      - Integer wavelengths (e.g., 396.0, 550.0) -> 'Rrs_396nm', 'Rrs_550nm'
      - Fractional wavelengths (e.g., 442.5)     -> 'Rrs_442.5nm'
    """
    if abs(wavelength_nm - round(wavelength_nm)) < 1e-6:
        return f"{prefix}_{int(round(wavelength_nm))}nm"
    return f"{prefix}_{wavelength_nm:g}nm"


def locate_m_file(root_name: str, config: SimulationConfig) -> Optional[str]:
    """
    Searches standard HydroLight output folders (with recursive fallback under
    `config.he60_dir`) for `M<root_name>.txt`.
    """
    target_name = f"M{root_name}.txt"
    for folder in config.output_search_dirs:
        candidate = os.path.join(folder, target_name)
        if os.path.exists(candidate):
            return candidate

    matches = glob.glob(os.path.join(config.he60_dir, "**", target_name), recursive=True)
    return matches[0] if matches else None


def parse_msab_output(
    m_file_path: Optional[str],
) -> Tuple[Optional[List[float]], Optional[List[float]], Optional[float], Dict[float, float]]:
    """
    Parses a HydroLight `M<root_name>.txt` file and returns:
      1. `wavelengths`: List of all simulated band center wavelengths (nm)
      2. `rrs_values`:  List of Rrs(lambda) (1/sr) matching `wavelengths`
      3. `bb_550`:      Total backscattering bb (1/m) at 550 nm (or closest band)
      4. `bb_spectrum`: Dictionary mapping {wavelength_nm: bb_total_m1} across all bands
    """
    if not m_file_path or not os.path.exists(m_file_path):
        return None, None, None, {}

    wavelengths: List[float] = []
    rrs_values: List[float] = []
    bb_spectrum: Dict[float, float] = {}

    with open(m_file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    in_rrs_block = False
    in_bb_block = False

    for line in lines:
        stripped = line.strip()

        # Enter the "Rrs" sheet
        if '"Rrs"' in line and '"Rrs (1/sr)"' in line:
            in_rrs_block = True
            in_bb_block = False
            continue

        if in_rrs_block:
            if stripped == "" or (stripped.startswith('"') and not stripped.startswith('" "')):
                in_rrs_block = False
                continue

            parts = stripped.split()
            if len(parts) >= 2 and not stripped.startswith('"'):
                try:
                    wl = float(parts[0])
                    rrs = float(parts[1])
                    wavelengths.append(wl)
                    rrs_values.append(rrs)
                except ValueError:
                    pass

        # Enter the total backscattering "bb" sheet
        if '"bb"' in line and '"backscat coef' in line:
            in_bb_block = True
            in_rrs_block = False
            continue

        if in_bb_block:
            if stripped == "" or (stripped.startswith('"') and not stripped.startswith('" "')):
                in_bb_block = False
                continue

            parts = stripped.split()
            if len(parts) >= 2 and not stripped.startswith('"'):
                try:
                    wl = float(parts[0])
                    bb_surface = float(parts[1])
                    bb_spectrum[wl] = bb_surface
                except ValueError:
                    pass

    # Extract bb at 550 nm (or nearest available wavelength for multispectral runs)
    bb_550: Optional[float] = None
    if bb_spectrum:
        bb_wls = np.array(list(bb_spectrum.keys()), dtype=float)
        nearest_wl = float(bb_wls[np.argmin(np.abs(bb_wls - 550.0))])
        bb_550 = bb_spectrum[nearest_wl]

    return wavelengths, rrs_values, bb_550, bb_spectrum
