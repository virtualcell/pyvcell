from pathlib import Path

import numpy as np

from pyvcell.data_model.result import Result
from pyvcell.data_model.simulation import SpatialSimulation
from pyvcell.data_model.spatial_model import SpatialModel


def test_model_parse_1D(sbml_spatial_model_1D_path: Path) -> None:
    assert sbml_spatial_model_1D_path.is_file()

    spatial_model = SpatialModel(filepath=sbml_spatial_model_1D_path)
    assert spatial_model is not None
    parameters: dict[str, float] = spatial_model.copy_parameters()
    assert parameters == {
        "Kf_r0": 1.0,
        "Kr_r0": 0.5,
        "_F_": 96485.3321,
        "s0_BC_Xm": 0.0,
        "s0_BC_Xp": 0.0,
        "s0_diff": 1e-09,
        "s1_BC_Xm": 0.0,
        "s1_BC_Xp": 0.0,
        "s1_diff": 1e-09,
        "x": 0.0,
    }

    simulation_orig = SpatialSimulation(model=spatial_model)
    results_orig: Result = simulation_orig.run()

    spatial_model.set_parameter_value("Kr_r0", 100.0)
    assert spatial_model.model.getParameter("Kr_r0").getValue() == 100.0

    simulation_changed = SpatialSimulation(model=spatial_model)
    results_changed: Result = simulation_changed.run()

    channels_orig = results_orig.channels
    channels_changed = results_changed.channels
    assert [channel.label for channel in channels_orig] == ["s0", "s1", "J_r0", "s0_init_umol_l_1", "s1_init_umol_l_1"]
    assert [channel.label for channel in channels_changed] == [
        "s0",
        "s1",
        "J_r0",
        "s0_init_umol_l_1",
        "s1_init_umol_l_1",
    ]
    assert np.allclose(
        results_orig.concentrations[0, 0::10],
        np.array(
            [
                500000.00000000006,
                111567.6365951872,
                24896.679062681855,
                5557.782130200425,
                1242.6980776316473,
                279.87288513273455,
            ],
            dtype=np.float64,
        ),
    )
    assert np.allclose(
        results_changed.concentrations[0, 0::10],
        np.array(
            [
                500000.00000000006,
                9.900990099008627,
                9.900990098975953,
                9.900990099033788,
                9.90099009925654,
                9.900990100225261,
            ],
            dtype=np.float64,
        ),
    )


def test_model_parse_3D(sbml_spatial_model_3D_path: Path) -> None:
    assert sbml_spatial_model_3D_path.is_file()

    spatial_model = SpatialModel(filepath=sbml_spatial_model_3D_path)
    assert spatial_model is not None
    parameters: dict[str, float] = spatial_model.copy_parameters()
    assert parameters == {
        "Kf_r0": 1.0,
        "Kf_r1": 1.0,
        "Kf_r2": 1.0,
        "Kr_r0": 0.5,
        "Kr_r1": 1.0,
        "Kr_r2": 1.0,
        "Voltage_m0": 0.0,
        "_F_": 96485.3321,
        "s0_BC_Xm": 0.0,
        "s0_BC_Xp": 0.0,
        "s0_BC_Ym": 0.0,
        "s0_BC_Yp": 0.0,
        "s0_BC_Zm": 0.0,
        "s0_BC_Zp": 0.0,
        "s0_diff": 0.0001,
        "s1_BC_Xm": 0.0,
        "s1_BC_Xp": 0.0,
        "s1_BC_Ym": 0.0,
        "s1_BC_Yp": 0.0,
        "s1_BC_Zm": 0.0,
        "s1_BC_Zp": 0.0,
        "s1_diff": 0.0001,
        "s2_BC_Xm": 0.0,
        "s2_BC_Xp": 0.0,
        "s2_BC_Ym": 0.0,
        "s2_BC_Yp": 0.0,
        "s2_BC_Zm": 0.0,
        "s2_BC_Zp": 0.0,
        "s2_diff": 1.0000000000000002e-06,
        "s3_BC_Xm": 0.0,
        "s3_BC_Xp": 0.0,
        "s3_BC_Ym": 0.0,
        "s3_BC_Yp": 0.0,
        "s3_BC_Zm": 0.0,
        "s3_BC_Zp": 0.0,
        "s3_diff": 0.0001,
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
    }

    simulation_orig = SpatialSimulation(model=spatial_model)
    results_orig: Result = simulation_orig.run()

    spatial_model.set_parameter_value("Kr_r0", 100.0)
    assert spatial_model.model.getParameter("Kr_r0").getValue() == 100.0

    simulation_changed = SpatialSimulation(model=spatial_model)
    results_changed: Result = simulation_changed.run()

    channels_orig = results_orig.channels
    channels_changed = results_changed.channels
    assert [channel.label for channel in channels_orig] == [
        "s0",
        "s1",
        "s3",
        "J_r0",
        "s0_init_umol_l_1",
        "s1_init_umol_l_1",
        "s3_init_umol_l_1",
    ]
    assert [channel.label for channel in channels_changed] == [
        "s0",
        "s1",
        "s3",
        "J_r0",
        "s0_init_umol_l_1",
        "s1_init_umol_l_1",
        "s3_init_umol_l_1",
    ]
    assert np.allclose(
        results_orig.concentrations[0, 0::10],
        np.array(
            [
                0.9437660084383092,
                0.6361978498031116,
                0.5686143581466128,
                0.5534685810896134,
                0.5500565078980726,
                0.5492825303078028,
            ],
            dtype=np.float64,
        ),
    )
    assert np.allclose(
        results_changed.concentrations[0, 0::10],
        np.array(
            [
                0.9437660084383092,
                1.5951835187732106,
                1.5950442251682273,
                1.5949523994085677,
                1.5948608188247102,
                1.594764708696783,
            ],
            dtype=np.float64,
        ),
    )
