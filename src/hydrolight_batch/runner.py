"""
STEP 6: End-to-End Parallel Batch Runner & Incremental CSV Exporter
-------------------------------------------------------------------
Coordinates the complete workflow from start to finish:
  1. Inspects the user's I***.txt template to detect components, band count,
     wavelength range, and multispectral vs hyperspectral classification.
  2. Initializes isolated worker sandboxes (backend_w1 .. backend_wN).
  3. Generates the reproducible parameter manifest (Chla, CDOM, Minerals/TSS, bb/b).
  4. Executes HydroLight6.exe in parallel across workers with scratch scrubbing.
  5. Parses full-range Rrs(lambda) and bb outputs from M***.txt.
  6. Streams each completed simulation row immediately to the master CSV file.
"""

from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import subprocess
import time
from typing import Any, Dict, Optional
import numpy as np
import pandas as pd

from .config import SimulationConfig
from .parser import format_wavelength_col, locate_m_file, parse_msab_output
from .sampling import generate_parameter_manifest
from .sandbox import (
    clean_sandbox_scratch_files,
    cleanup_all_run_files,
    initialize_worker_sandboxes,
)
from .template import TemplateMetadata, inspect_template, render_run_input


def execute_single_simulation(
    param: Dict[str, Any],
    template_meta: TemplateMetadata,
    config: SimulationConfig,
) -> Optional[Dict[str, Any]]:
    """
    Runs a single HydroLight 6.0 simulation inside an isolated worker sandbox,
    parses the full-range Rrs spectrum and bb values, cleans temporary files,
    and returns a dictionary row ready for CSV export.
    """
    root_name = param["root_name"]
    irun_filename = f"I{root_name}.txt"
    irun_path = os.path.join(config.batch_dir, irun_filename)

    worker_id = ((param["run_index"] - 1) % config.max_workers) + 1
    sandbox_dir = config.sandbox_dir(worker_id)

    # 1. Scrub leftover Fortran scratch files prior to launching solver
    clean_sandbox_scratch_files(sandbox_dir)

    if config.stagger_seconds > 0:
        time.sleep((param["run_index"] % config.max_workers) * config.stagger_seconds)

    # 2. Render customized I<root_name>.txt preserving template components & bands
    run_lines = render_run_input(
        template_meta=template_meta,
        root_name=root_name,
        chl=param["chl"],
        cdom=param["cdom"],
        minerals=param["minerals"],
        bb_ratio=param["bb_ratio"],
        chl_idx=config.chl_component_idx,
        cdom_idx=config.cdom_component_idx,
        minerals_idx=config.minerals_component_idx,
    )

    with open(irun_path, "w", encoding="utf-8") as f:
        f.writelines(run_lines)

    # 3. Invoke HydroLight6.exe inside the isolated sandbox
    rel_input_path = os.path.relpath(irun_path, sandbox_dir)
    cmd = f"HydroLight6.exe < {rel_input_path}"

    try:
        subprocess.run(
            cmd,
            shell=True,
            cwd=sandbox_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=config.timeout_seconds,
        )
    except Exception:
        cleanup_all_run_files(root_name, config)
        clean_sandbox_scratch_files(sandbox_dir)
        return None

    # 4. Locate M<root_name>.txt and extract full-range Rrs(lambda) & bb
    m_file_path = locate_m_file(root_name, config)
    wavelengths, rrs_values, bb_total_550, bb_spectrum = parse_msab_output(m_file_path)

    result_row: Optional[Dict[str, Any]] = None
    if rrs_values and len(rrs_values) > 0 and wavelengths:
        result_row = {
            "RunID": root_name,
            "Chla_mg_m3": param["chl"],
            "CDOM_m1": param["cdom"],
            "Minerals_mg_L": param["minerals"],
            "bb_ratio_input": param["bb_ratio"],
            "bb_total_550nm": bb_total_550 if bb_total_550 is not None else np.nan,
        }

        # Save all simulated Rrs bands across the full wavelength range from I***.txt
        for wl, rrs in zip(wavelengths, rrs_values):
            result_row[format_wavelength_col(wl, prefix="Rrs")] = float(rrs)

        # Optionally save full-spectrum bb_<wl>nm columns as well
        if config.include_full_bb_spectrum and bb_spectrum:
            for wl in wavelengths:
                bb_val = bb_spectrum.get(wl, np.nan)
                result_row[format_wavelength_col(wl, prefix="bb")] = float(bb_val)

    # 5. Clean up intermediate files and post-run Fortran scratch files
    cleanup_all_run_files(root_name, config)
    clean_sandbox_scratch_files(sandbox_dir)
    return result_row


def append_to_csv_safe(
    df_single: pd.DataFrame,
    csv_filepath: str,
    header_needed: bool,
    max_retries: int = 5,
) -> bool:
    """
    Appends a single result row to the output CSV file with automatic retry
    protection if the file is temporarily locked by Excel or antivirus software.
    """
    for attempt in range(max_retries):
        try:
            if header_needed:
                df_single.to_csv(csv_filepath, mode="w", index=False)
            else:
                df_single.to_csv(csv_filepath, mode="a", header=False, index=False)
            return True
        except PermissionError:
            print(
                f"\nWarning: '{csv_filepath}' is locked (e.g., open in Excel). "
                f"Retrying in 2s ({attempt + 1}/{max_retries})..."
            )
            time.sleep(2)
    return False


class BatchRunner:
    """
    High-level orchestrator for running end-to-end HydroLight simulation batches.
    """

    def __init__(self, config: SimulationConfig = SimulationConfig()):
        self.config = config

    def run(self) -> TemplateMetadata:
        cfg = self.config
        b = cfg.bounds

        # Step A: Inspect the user's I***.txt template file dynamically
        template_meta = inspect_template(
            cfg.template_file,
            minerals_component_idx=cfg.minerals_component_idx,
        )

        print("=" * 88)
        print(f"  HYDROLIGHT PARALLEL PIPELINE ({cfg.max_workers}-WORKER SANDBOXED MODE - {cfg.n_runs} RUNS)")
        print("=" * 88)
        print(template_meta.summary_text())
        print("-" * 88)
        print(f" Target Simulation Count (N_RUNS) : {cfg.n_runs}")
        print(f" Active Parallel Workers          : {cfg.max_workers} Workers (Sandboxed & Scrubbed)")
        print(f" Subprocess Timeout Ceiling       : {cfg.timeout_seconds} seconds")
        print(f" Chla Range  (Log-Uniform)        : {b.chl_min} - {b.chl_max} mg/m^3")
        print(f" Minerals/TSS (Log-Uniform)       : {b.minerals_min} - {b.minerals_max} mg/L")
        print(f" CDOM Range  (Log-Uniform)        : {b.cdom_min} - {b.cdom_max} m^-1")
        print(f" bb/b Ratio  (Uniform)            : {b.bb_ratio_min} - {b.bb_ratio_max}")
        print(f" Master Output CSV File           : {cfg.output_csv}")
        print("=" * 88)

        # Step B: Prepare sandbox directories and output folders
        print(f"Initializing {cfg.max_workers} worker sandbox environments...")
        initialize_worker_sandboxes(cfg)

        os.makedirs(cfg.batch_dir, exist_ok=True)
        for folder in cfg.output_search_dirs:
            os.makedirs(folder, exist_ok=True)

        # Step C: Generate parameter manifest
        params_list = generate_parameter_manifest(
            n_runs=cfg.n_runs,
            bounds=cfg.bounds,
            seed=cfg.seed,
            run_prefix=cfg.run_prefix,
        )

        # Step D: Handle fresh start vs resume mode
        header_written = False
        completed_ids = set()

        if os.path.exists(cfg.output_csv):
            if cfg.resume:
                existing_df = pd.read_csv(cfg.output_csv)
                if "RunID" in existing_df.columns and len(existing_df) > 0:
                    completed_ids = set(existing_df["RunID"].astype(str))
                    header_written = True
                    print(f"Resume mode active: skipping {len(completed_ids)} already saved runs.\n")
            else:
                try:
                    os.remove(cfg.output_csv)
                    print(f"Notice: Cleared previous '{cfg.output_csv}' to start fresh batch.\n")
                except PermissionError:
                    print(f"ERROR: Please close '{cfg.output_csv}' in Excel before starting!")
                    return template_meta

        pending_params = [p for p in params_list if p["root_name"] not in completed_ids]
        start_time = time.time()
        completed_count = len(completed_ids)
        saved_count = len(completed_ids)

        print(f"Launching {cfg.max_workers} parallel workers for {len(pending_params)} pending runs...\n")

        # Step E: Parallel execution & incremental CSV streaming
        with ProcessPoolExecutor(max_workers=cfg.max_workers) as executor:
            futures = {
                executor.submit(execute_single_simulation, param, template_meta, cfg): param
                for param in pending_params
            }

            for future in as_completed(futures):
                completed_count += 1
                param_info = futures[future]
                result_row = future.result()
                elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - start_time))

                if result_row is not None:
                    df_single = pd.DataFrame([result_row])
                    success = append_to_csv_safe(df_single, cfg.output_csv, not header_written)
                    if success:
                        header_written = True
                        saved_count += 1

                    print(
                        f"[{completed_count:4d}/{cfg.n_runs:4d}] {result_row['RunID']} Saved | "
                        f"Chl: {result_row['Chla_mg_m3']:7.4f} | CDOM: {result_row['CDOM_m1']:6.4f} | "
                        f"TSS: {result_row['Minerals_mg_L']:7.2f} | Bands: {template_meta.n_bands} | Time: {elapsed}"
                    )
                else:
                    print(
                        f"[{completed_count:4d}/{cfg.n_runs:4d}] {param_info['root_name']} Failed | "
                        f"Chl: {param_info['chl']:7.4f} | CDOM: {param_info['cdom']:6.4f} | "
                        f"TSS: {param_info['minerals']:7.2f} | Time: {elapsed}"
                    )

        total_elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - start_time))
        print("=" * 88)
        print(" BATCH EXECUTION COMPLETE!")
        print(f" Sensor Regime           : {template_meta.sensor_type.upper()} ({template_meta.n_bands} bands)")
        print(f" Total Runs Processed    : {completed_count}/{cfg.n_runs}")
        print(f" Valid Spectra Saved     : {saved_count}/{cfg.n_runs}")
        print(f" Total Execution Time    : {total_elapsed}")
        print(f" Dataset Saved To        : {os.path.abspath(cfg.output_csv)}")
        print("=" * 88)
        return template_meta
