"""
Automated Unit & End-to-End Pipeline Tests for hydrolight-batch
-----------------------------------------------------------------
Author: Md Masud-Ul-Alam (ORCID: https://orcid.org/0000-0003-3036-8167)
"""

import os
import tempfile

from hydrolight_batch import (
    SimulationConfig,
    generate_parameter_manifest,
    inspect_template,
    parse_msab_output,
    render_run_input,
)


def _create_multispectral_template(path: str, base_isab2_path: str) -> None:
    """Creates a synthetic 8-band multispectral template from ISAB2.txt."""
    with open(base_isab2_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    lines[1] = "Multispectral Sentinel-2 Test\n"
    lines[2] = "MS2\n"
    lines[31] = "8\n"
    lines[32] = "433,453,480,500,545,575,650,680,715\n"
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def run_all_tests(isab_path: str, isab2_path: str, msab_path: str) -> None:
    # 0. Verify default n_runs is 5
    default_cfg = SimulationConfig()
    assert default_cfg.n_runs == 5
    default_manifest = generate_parameter_manifest()
    assert len(default_manifest) == 5

    # 1. Test 5-component hyperspectral template (ISAB.txt)
    meta5 = inspect_template(isab_path)
    assert meta5.n_components == 5
    assert meta5.n_bands == 165
    assert meta5.sensor_type == "hyperspectral"
    assert meta5.band_centers_nm[0] == 396.0
    assert meta5.band_centers_nm[-1] == 724.0

    rendered5 = render_run_input(meta5, "SAB_0001", chl=1.23456, cdom=0.12345, minerals=45.6789, bb_ratio=0.025)
    assert rendered5[2].strip() == "SAB_0001"
    assert len(rendered5[6].split(",")) == 5
    assert "1.23456" in rendered5[6]
    assert "0.0250" in rendered5[10]

    # 2. Test 4-component hyperspectral template (ISAB2.txt)
    meta4 = inspect_template(isab2_path)
    assert meta4.n_components == 4
    assert meta4.n_bands == 165
    assert meta4.sensor_type == "hyperspectral"

    rendered4 = render_run_input(meta4, "SAB_0002", chl=2.5, cdom=0.05, minerals=12.0, bb_ratio=0.018)
    assert rendered4[2].strip() == "SAB_0002"
    assert len(rendered4[6].split(",")) == 4
    assert "2.50000" in rendered4[6]
    assert "0.0180" in rendered4[10]

    # 3. Test multispectral template detection
    with tempfile.TemporaryDirectory() as tmpdir:
        ms_tpl = os.path.join(tmpdir, "IMS2.txt")
        _create_multispectral_template(ms_tpl, isab2_path)
        meta_ms = inspect_template(ms_tpl)
        assert meta_ms.n_bands == 8
        assert meta_ms.sensor_type == "multispectral"
        assert meta_ms.band_centers_nm[0] == 443.0

    # 4. Test M***.txt parser
    wls, rrs, bb550, bb_spec = parse_msab_output(msab_path)
    assert len(wls) == 165
    assert len(rrs) == 165
    assert wls[0] == 396.0 and wls[-1] == 724.0
    assert bb550 is not None and bb550 > 0
    assert len(bb_spec) == 165

    print("All default-5, template inspection, rendering, and parser assertions passed!")
