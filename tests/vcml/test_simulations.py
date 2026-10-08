from pathlib import Path

import numpy as np

import pyvcell.vcml as vc
from pyvcell.sim_results.result import Result


def test_vcml_model_parse_3d(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    bio_model = vc.load_vcml_file(vcml_spatial_model_1d_path)
    assert bio_model.model is not None
    parameters: list[vc.ModelParameter] = bio_model.model.model_parameters
    assert {p.name: p.value for p in parameters} == {"Kf_r0": 1.0, "Kr_r0": 0.5}

    sim_name = bio_model.applications[0].simulations[0].name
    results_orig: Result = vc.simulate(bio_model, sim_name)

    Kr_r0 = next(p for p in bio_model.model.model_parameters if p.name == "Kr_r0")
    Kr_r0.value = 100.0

    results_changed = vc.simulate(bio_model, sim_name)

    channels_orig = results_orig.channel_data
    channels_changed = results_changed.channel_data
    assert [channel.label for channel in channels_orig] == [
        "region_mask",
        "t",
        "x",
        "y",
        "z",
        "s0",
        "s1",
        "J_r0",
        "s0_init_uM",
        "s1_init_uM",
    ]
    assert [channel.label for channel in channels_changed] == [
        "region_mask",
        "t",
        "x",
        "y",
        "z",
        "s0",
        "s1",
        "J_r0",
        "s0_init_uM",
        "s1_init_uM",
    ]
    assert np.allclose(
        results_orig.concentrations[0, 0::10],
        np.array(
            [500000.00000000006, 236185.00811512678, 111567.6111715472],
            dtype=np.float64,
        ),
    )
    assert np.allclose(
        results_changed.concentrations[0, 0::10],
        np.array(
            [500000.00000000006, 9.900990099017005, 9.900990099052574],
            dtype=np.float64,
        ),
    )
