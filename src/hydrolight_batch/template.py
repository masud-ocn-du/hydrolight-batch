"""
STEP 2: Dynamic HydroLight Template (I***.txt) Inspector & Modifier
--------------------------------------------------------------------
Reads any HydroLight 6.0 input file (ISAB.txt, ISAB2.txt, Itest.txt, etc.) to
automatically extract:
  - Run title and template root name
  - Number of optical components (ncomp, e.g. 4 or 5 components)
  - Number of wavelength bands (n_bands)
  - Band boundary edges (n_bands + 1 values) and band center wavelengths (nm)
  - Spectral resolution (bandwidths in nm)
  - Sensor regime classification: 'hyperspectral' vs 'multispectral'

Also dynamically injects sampled concentrations (Chla, CDOM, Minerals/TSS) and
mineral bb/b ratios into the exact line positions for that specific template.
"""

from dataclasses import dataclass
import os
import re
from typing import List, Tuple
import numpy as np


@dataclass
class TemplateMetadata:
    """
    Structured metadata extracted automatically from any HydroLight I***.txt file.
    """
    template_path: str
    run_title: str
    template_root_name: str
    n_components: int
    concentrations_line_idx: int
    bb_ratio_line_idx: int
    n_bands: int
    band_edges_nm: List[float]
    band_centers_nm: List[float]
    bandwidths_nm: List[float]
    wavelength_min_nm: float
    wavelength_max_nm: float
    median_bandwidth_nm: float
    sensor_type: str  # "hyperspectral" or "multispectral"
    raw_lines: List[str]

    def summary_text(self) -> str:
        """Returns a formatted multi-line summary of the template configuration."""
        return (
            f"Template File          : {os.path.abspath(self.template_path)}\n"
            f"Run Title              : {self.run_title}\n"
            f"Template Root Name     : {self.template_root_name}\n"
            f"Optical Components     : {self.n_components} components\n"
            f"Spectral Classification: {self.sensor_type.upper()} ({self.n_bands} bands)\n"
            f"Band Center Range      : {self.wavelength_min_nm:g} nm - {self.wavelength_max_nm:g} nm\n"
            f"Band Edge Range        : {self.band_edges_nm[0]:g} nm - {self.band_edges_nm[-1]:g} nm\n"
            f"Median Bandwidth (FWHM): {self.median_bandwidth_nm:.2f} nm"
        )


def classify_spectral_regime(n_bands: int, bandwidths_nm: List[float]) -> str:
    """
    Classifies a template's wavelength configuration as 'hyperspectral' or
    'multispectral' based on band count and median spectral bandwidth.

    Standard remote sensing convention:
      - Hyperspectral: >= 30 bands with contiguous narrow spacing (median <= 15 nm),
        or >= 50 bands overall.
      - Multispectral: < 30 discrete/broad bands (e.g., Sentinel-2 MSI, Landsat OLI,
        MODIS, SeaWiFS, MERIS).
    """
    if n_bands == 0:
        return "unknown"
    median_bw = float(np.median(bandwidths_nm)) if bandwidths_nm else 0.0
    if (n_bands >= 30 and median_bw <= 15.0) or n_bands >= 50:
        return "hyperspectral"
    return "multispectral"


def _parse_numeric_tokens(line: str) -> List[float]:
    """Splits a comma- or whitespace-delimited HydroLight record into floats."""
    tokens = [t.strip() for t in re.split(r"[,\s]+", line.strip()) if t.strip()]
    return [float(t) for t in tokens]


def _extract_wavelength_grid(lines: List[str], n_components: int) -> Tuple[int, List[float]]:
    """
    Finds the wavelength band count (n_bands) and the (n_bands + 1) band edge
    wavelengths inside a HydroLight I***.txt file.

    In HydroLight 6.0 I***.txt files:
      - Line index 5 (Record 5a) specifies `ncomp, ncomp`
      - Line index 6 (Record 5b) specifies `ncomp` component concentrations
      - Next come 6 blocks of `ncomp` lines each (IOP model specs, astar files,
        absorption params, bstar files, scattering params, dpf files).
      - Immediately after those `6 * ncomp` lines (at index `7 + 6 * ncomp`) sits
        the single-integer `n_bands` record, followed by `n_bands + 1` wavelength
        boundary edges (which may span one or multiple lines).
    """
    expected_nbands_idx = 7 + 6 * n_components
    candidate_indices = []

    if 0 <= expected_nbands_idx < len(lines):
        candidate_indices.append(expected_nbands_idx)

    # Also scan nearby lines as a fallback in case custom templates add/omit header lines
    for idx in range(10, len(lines) - 1):
        if idx not in candidate_indices:
            candidate_indices.append(idx)

    for idx in candidate_indices:
        line_str = lines[idx].strip()
        if re.fullmatch(r"\d+", line_str):
            n_bands = int(line_str)
            if n_bands < 1 or n_bands > 5000:
                continue

            # Collect `n_bands + 1` monotonically increasing edge wavelengths
            collected_edges: List[float] = []
            cursor = idx + 1
            while cursor < len(lines) and len(collected_edges) < (n_bands + 1):
                try:
                    vals = _parse_numeric_tokens(lines[cursor])
                except ValueError:
                    break
                if not vals:
                    break
                collected_edges.extend(vals)
                cursor += 1

            if len(collected_edges) >= (n_bands + 1):
                edges = collected_edges[: n_bands + 1]
                # Verify edges are strictly increasing wavelengths (in nm)
                if all(edges[i] < edges[i + 1] for i in range(len(edges) - 1)) and edges[0] >= 100.0:
                    return n_bands, edges

    raise ValueError(
        "Could not locate valid wavelength band count and band edges in the HydroLight template file."
    )


def inspect_template(
    template_path: str,
    minerals_component_idx: int = 3,
) -> TemplateMetadata:
    """
    Parses any HydroLight I***.txt template file and returns a TemplateMetadata
    object describing its component structure, wavelength bands, and sensor type.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"HydroLight template file not found: '{template_path}'")

    with open(template_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_lines = f.readlines()

    if len(raw_lines) < 20:
        raise ValueError(f"Template '{template_path}' appears incomplete ({len(raw_lines)} lines).")

    run_title = raw_lines[1].strip()
    template_root_name = raw_lines[2].strip()

    # Record 5a (line index 5): `<ncomp>, <ncomp>` (e.g., `5, 5` in ISAB.txt or `4, 4` in ISAB2.txt)
    comp_header_vals = _parse_numeric_tokens(raw_lines[5])
    n_components = int(comp_header_vals[0])

    # Record 5b (line index 6): `<ncomp>` concentration values
    concentrations_line_idx = 6
    conc_vals = _parse_numeric_tokens(raw_lines[concentrations_line_idx])
    if len(conc_vals) != n_components:
        raise ValueError(
            f"Mismatch in '{template_path}': Record 5a declares {n_components} components, "
            f"but line 7 has {len(conc_vals)} concentration entries."
        )

    # Component IOP model lines immediately follow line 6 (indices 7 .. 7 + n_components - 1)
    bb_ratio_line_idx = 7 + minerals_component_idx

    # Extract wavelength band count and edges
    n_bands, band_edges = _extract_wavelength_grid(raw_lines, n_components)
    band_centers = [0.5 * (band_edges[i] + band_edges[i + 1]) for i in range(n_bands)]
    bandwidths = [band_edges[i + 1] - band_edges[i] for i in range(n_bands)]

    sensor_type = classify_spectral_regime(n_bands, bandwidths)

    return TemplateMetadata(
        template_path=template_path,
        run_title=run_title,
        template_root_name=template_root_name,
        n_components=n_components,
        concentrations_line_idx=concentrations_line_idx,
        bb_ratio_line_idx=bb_ratio_line_idx,
        n_bands=n_bands,
        band_edges_nm=band_edges,
        band_centers_nm=band_centers,
        bandwidths_nm=bandwidths,
        wavelength_min_nm=min(band_centers),
        wavelength_max_nm=max(band_centers),
        median_bandwidth_nm=float(np.median(bandwidths)),
        sensor_type=sensor_type,
        raw_lines=raw_lines,
    )


def render_run_input(
    template_meta: TemplateMetadata,
    root_name: str,
    chl: float,
    cdom: float,
    minerals: float,
    bb_ratio: float,
    chl_idx: int = 1,
    cdom_idx: int = 2,
    minerals_idx: int = 3,
) -> List[str]:
    """
    Creates customized I<root_name>.txt lines for a single simulation run while
    preserving the exact component count (4, 5, etc.) and spectral grid of the
    underlying template file.
    """
    run_lines = template_meta.raw_lines.copy()

    # 1. Update run root name (line index 2)
    run_lines[2] = f"{root_name}\n"

    # 2. Update component concentrations (line index 6) dynamically for any n_components
    conc_tokens = [t.strip() for t in run_lines[template_meta.concentrations_line_idx].strip().split(",")]
    if max(chl_idx, cdom_idx, minerals_idx) >= len(conc_tokens):
        raise IndexError(
            f"Template has only {len(conc_tokens)} components, cannot assign index "
            f"{max(chl_idx, cdom_idx, minerals_idx)}."
        )
    conc_tokens[chl_idx] = f"{chl:.5f}"
    conc_tokens[cdom_idx] = f"{cdom:.5f}"
    conc_tokens[minerals_idx] = f"{minerals:.4f}"
    run_lines[template_meta.concentrations_line_idx] = ", ".join(conc_tokens) + "\n"

    # 3. Update mineral particle backscattering ratio bb/b on the mineral IOP spec line
    bb_tokens = [t.strip() for t in run_lines[template_meta.bb_ratio_line_idx].strip().split(",")]
    if len(bb_tokens) >= 5:
        bb_tokens[4] = f"{bb_ratio:.4f}"
        run_lines[template_meta.bb_ratio_line_idx] = ", ".join(bb_tokens) + "\n"
    else:
        run_lines[template_meta.bb_ratio_line_idx] = f"0, 0, 440, 1, {bb_ratio:.4f}\n"

    return run_lines
