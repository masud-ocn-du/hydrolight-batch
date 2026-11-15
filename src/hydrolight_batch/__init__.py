"""
hydrolight_batch
================
Template-driven parallel HydroLight 6.0 simulation pipeline for generating
hyperspectral and multispectral Rrs, IOP, and TSS datasets.

Author: Md Masud-Ul-Alam (ORCID: https://orcid.org/0000-0003-3036-8167)
Affiliation: UGA Skidaway Institute of Oceanography
Repository: https://github.com/masud-ocn-du/hydrolight-batch
"""

from .config import ParameterBounds, SimulationConfig
from .template import TemplateMetadata, inspect_template, render_run_input
from .sampling import generate_parameter_manifest
from .sandbox import (
    clean_sandbox_scratch_files,
    cleanup_all_run_files,
    initialize_worker_sandboxes,
)
from .parser import format_wavelength_col, locate_m_file, parse_msab_output
from .runner import BatchRunner, execute_single_simulation

__version__ = "1.0.0"
__author__ = "Md Masud-Ul-Alam"
__orcid__ = "https://orcid.org/0000-0003-3036-8167"

__all__ = [
    "__version__",
    "__author__",
    "__orcid__",
    "ParameterBounds",
    "SimulationConfig",
    "TemplateMetadata",
    "inspect_template",
    "render_run_input",
    "generate_parameter_manifest",
    "initialize_worker_sandboxes",
    "clean_sandbox_scratch_files",
    "cleanup_all_run_files",
    "locate_m_file",
    "parse_msab_output",
    "format_wavelength_col",
    "execute_single_simulation",
    "BatchRunner",
]
