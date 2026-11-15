"""
Beginner-to-End Example Script for Running HydroLight Batches
-------------------------------------------------------------
1. Place this script inside your HydroLight working folder (e.g., C:\HE60\work)
   alongside your HydroLight template file (e.g., ISAB.txt or ISAB2.txt).
2. By default, `n_runs = 5` runs 5 quick simulations to verify your setup.
   Simply change `n_runs` (e.g., `n_runs = 500`, `5000`, or `8000`) to generate
   your desired dataset size!
3. Run:
       python run_batch_from_template.py
"""

from hydrolight_batch import (
    BatchRunner,
    ParameterBounds,
    SimulationConfig,
    inspect_template,
)

if __name__ == "__main__":
    TEMPLATE_PATH = "ISAB.txt"

    # Step 1: Preview what the package detects inside your template file
    meta = inspect_template(TEMPLATE_PATH)
    print(meta.summary_text())
    print()

    # Step 2: Configure your batch run (automatically uses all bands from TEMPLATE_PATH)
    config = SimulationConfig(
        n_runs=5,                        # Default = 5 simulations; change to any number (e.g., 500, 5000, 8000)
        max_workers=8,
        timeout_seconds=900,
        seed=101,
        he60_dir=r"C:\HE60",
        template_file=TEMPLATE_PATH,
        output_csv="HydroLight_Rrs_bb_Dataset.csv",
        include_full_bb_spectrum=False,  # Set True to also export bb_<wl>nm for every band
        resume=False,                    # Set True to resume an interrupted CSV run
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

    # Step 3: Execute parallel simulations and save CSV
    runner = BatchRunner(config)
    runner.run()
