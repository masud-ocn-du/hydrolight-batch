"""
STEP 7: Command-Line Interface (CLI)
------------------------------------
Provides terminal commands for users who prefer running batches or inspecting
HydroLight templates without writing Python scripts:
  1. `hydrolight-batch inspect-template --template ISAB.txt`
  2. `hydrolight-batch run --template ISAB.txt --n-runs 5 --output dataset.csv`
"""

import argparse
from .config import ParameterBounds, SimulationConfig
from .runner import BatchRunner
from .template import inspect_template


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hydrolight-batch",
        description="Template-driven parallel HydroLight 6.0 simulation runner for Rrs, IOP & TSS datasets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand 1: inspect-template
    insp_p = subparsers.add_parser(
        "inspect-template",
        help="Inspect an I***.txt template file to view band count, wavelength range, and sensor type.",
    )
    insp_p.add_argument("--template", required=True, help="Path to HydroLight input template (e.g., ISAB.txt)")
    insp_p.add_argument("--minerals-idx", type=int, default=3, help="0-based component index for Minerals/TSS (default: 3)")

    # Subcommand 2: run
    run_p = subparsers.add_parser(
        "run",
        help="Run a parallel HydroLight batch using the full spectral grid defined in the template file.",
    )
    run_p.add_argument("--template", default="ISAB.txt", help="HydroLight I***.txt template file (default: ISAB.txt)")
    run_p.add_argument("--n-runs", type=int, default=5, help="Total simulations to execute (default: 5)")
    run_p.add_argument("--workers", type=int, default=8, help="Number of parallel sandbox workers (default: 8)")
    run_p.add_argument("--timeout", type=int, default=900, help="Per-simulation timeout in seconds (default: 900)")
    run_p.add_argument("--seed", type=int, default=101, help="Random seed for parameter sampling (default: 101)")
    run_p.add_argument("--he60-dir", default=r"C:\HE60", help="HydroLight root directory (default: C:\HE60)")
    run_p.add_argument("--output", default="HydroLight_Rrs_bb_Dataset.csv", help="Output CSV file path")
    run_p.add_argument("--run-prefix", default="SAB", help="RunID prefix, max 4 chars (default: SAB)")
    run_p.add_argument("--include-full-bb", action="store_true", help="Also export bb_<wl>nm for every band")
    run_p.add_argument("--resume", action="store_true", help="Resume an existing CSV file without overwriting")

    # Component slot indices (for custom I***.txt setups)
    run_p.add_argument("--chl-idx", type=int, default=1, help="0-based component index for Chla (default: 1)")
    run_p.add_argument("--cdom-idx", type=int, default=2, help="0-based component index for CDOM (default: 2)")
    run_p.add_argument("--minerals-idx", type=int, default=3, help="0-based component index for Minerals/TSS (default: 3)")

    # Constituent sampling bounds
    run_p.add_argument("--chl-min", type=float, default=0.001)
    run_p.add_argument("--chl-max", type=float, default=50.0)
    run_p.add_argument("--cdom-min", type=float, default=0.003)
    run_p.add_argument("--cdom-max", type=float, default=0.8)
    run_p.add_argument("--minerals-min", type=float, default=1.0)
    run_p.add_argument("--minerals-max", type=float, default=1000.0)
    run_p.add_argument("--bb-ratio-min", type=float, default=0.005)
    run_p.add_argument("--bb-ratio-max", type=float, default=0.050)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "inspect-template":
        meta = inspect_template(args.template, minerals_component_idx=args.minerals_idx)
        print("=" * 72)
        print("  HYDROLIGHT TEMPLATE INSPECTION REPORT")
        print("=" * 72)
        print(meta.summary_text())
        print("-" * 72)
        print(f"First 5 band centers (nm) : {[round(w, 2) for w in meta.band_centers_nm[:5]]}")
        print(f"Last  5 band centers (nm) : {[round(w, 2) for w in meta.band_centers_nm[-5:]]}")
        print("=" * 72)

    elif args.command == "run":
        bounds = ParameterBounds(
            chl_min=args.chl_min,
            chl_max=args.chl_max,
            cdom_min=args.cdom_min,
            cdom_max=args.cdom_max,
            minerals_min=args.minerals_min,
            minerals_max=args.minerals_max,
            bb_ratio_min=args.bb_ratio_min,
            bb_ratio_max=args.bb_ratio_max,
        )
        config = SimulationConfig(
            n_runs=args.n_runs,
            max_workers=args.workers,
            timeout_seconds=args.timeout,
            seed=args.seed,
            he60_dir=args.he60_dir,
            template_file=args.template,
            output_csv=args.output,
            run_prefix=args.run_prefix,
            chl_component_idx=args.chl_idx,
            cdom_component_idx=args.cdom_idx,
            minerals_component_idx=args.minerals_idx,
            include_full_bb_spectrum=args.include_full_bb,
            resume=args.resume,
            bounds=bounds,
        )
        BatchRunner(config).run()


if __name__ == "__main__":
    main()
