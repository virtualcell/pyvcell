import tarfile
import tempfile
from pathlib import Path

import numpy as np

from pyvcell.sbml.sbml_simulation import SbmlSpatialSimulation
from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel
from pyvcell.sim_results.result import Result
from pyvcell.vcml import Biomodel, ModelParameter, VcmlReader
from pyvcell.vcml.vcml_simulation import VcmlSpatialSimulation


def test_sbml_model_parse_1d(sbml_spatial_model_1d_path: Path) -> None:
    assert sbml_spatial_model_1d_path.is_file()

    spatial_model = SbmlSpatialModel(filepath=sbml_spatial_model_1d_path)
    assert spatial_model is not None
    parameters: dict[str, float | str] = spatial_model.copy_parameters()
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

    assert spatial_model.get_coordinate_symbols() == ["x"]

    simulation_orig = SbmlSpatialSimulation(sbml_model=spatial_model)
    # results_orig: Result = simulation_orig.run(duration=5.0, output_time_step=0.1)
    results_orig: Result = simulation_orig.run()

    spatial_model.set_parameter_value("Kr_r0", 100.0)
    assert spatial_model.model.getParameter("Kr_r0").getValue() == 100.0
    spatial_model.set_parameter_value("s0_BC_Xm", 1.0)

    simulation_changed = SbmlSpatialSimulation(sbml_model=spatial_model)
    #    results_changed: Result = simulation_changed.run(duration=5.0, output_time_step=0.1)
    results_changed: Result = simulation_changed.run()

    channels_orig = results_orig.channel_data
    channels_changed = results_changed.channel_data
    assert [ch.label for ch in channels_orig] == [
        "region_mask",
        "t",
        "x",
        "y",
        "z",
        "s0",
        "s1",
        "J_r0",
        "s0_init_umol_l_1",
        "s1_init_umol_l_1",
    ]
    assert [ch.label for ch in channels_changed] == [
        "region_mask",
        "t",
        "x",
        "y",
        "z",
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
            [5.00000000e05, 1.00980393e01, 1.02950689e01, 1.04920984e01, 1.06891278e01, 1.08861571e01],
            dtype=np.float64,
        ),
    )


def test_sbml_model_parse_3d(sbml_spatial_model_3d_path: Path) -> None:
    assert sbml_spatial_model_3d_path.is_file()

    spatial_model = SbmlSpatialModel(filepath=sbml_spatial_model_3d_path)
    assert spatial_model is not None
    parameters: dict[str, float | str] = spatial_model.copy_parameters()
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

    simulation_orig = SbmlSpatialSimulation(sbml_model=spatial_model)
    # results_orig: Result = simulation_orig.run(duration=5.0, output_time_step=0.1)
    results_orig: Result = simulation_orig.run()

    spatial_model.set_parameter_value("Kr_r0", 100.0)
    assert spatial_model.model.getParameter("Kr_r0").getValue() == 100.0

    simulation_changed = SbmlSpatialSimulation(sbml_model=spatial_model)
    # results_changed: Result = simulation_changed.run(duration=5.0, output_time_step=0.1)
    results_changed: Result = simulation_changed.run()

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
        "s3",
        "J_r0",
        "s0_init_umol_l_1",
        "s1_init_umol_l_1",
        "s3_init_umol_l_1",
    ]
    assert [channel.label for channel in channels_changed] == [
        "region_mask",
        "t",
        "x",
        "y",
        "z",
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


def test_vcml_model_parse_3d(vcml_spatial_model_1d_path: Path) -> None:
    assert vcml_spatial_model_1d_path.is_file()

    bio_model: Biomodel = VcmlReader.biomodel_from_file(vcml_source=vcml_spatial_model_1d_path)
    assert bio_model.model is not None
    parameters: list[ModelParameter] = bio_model.model.model_parameters
    assert {p.name: p.value for p in parameters} == {"Kf_r0": 1.0, "Kr_r0": 0.5}

    sim_name = bio_model.applications[0].simulations[0].name
    simulation_orig = VcmlSpatialSimulation(bio_model=bio_model)
    # # create a temporary file to write the VCML content to
    # vcml_path = Path(tempfile.mktemp(prefix="model_", suffix=".xml"))
    # vcml_spatial_model.export(vcml_path)
    results_orig: Result = simulation_orig.run(simulation_name=sim_name)

    Kr_r0: ModelParameter = next(p for p in bio_model.model.model_parameters if p.name == "Kr_r0")
    Kr_r0.value = 100.0

    simulation_changed = VcmlSpatialSimulation(bio_model=bio_model)
    results_changed: Result = simulation_changed.run(simulation_name=sim_name)

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


def test_vcml_field_data_demo(vcml_field_data_demo_path: Path, vcml_field_data_tgz_archive_path: Path) -> None:
    assert vcml_field_data_demo_path.is_file()

    # create a temporary parent directory with a subdirectory for simulation data and a subdirectory to extract the archive
    parent_dir = Path(tempfile.mkdtemp())
    sim_dir = parent_dir / "sim"
    sim_dir.mkdir()
    assert sim_dir.is_dir()

    with tarfile.open(vcml_field_data_tgz_archive_path, "r:gz") as tar:
        tar.extractall(parent_dir)

    data_dir = parent_dir / "test2_lsm_DEMO"
    assert data_dir.is_dir()

    bio_model: Biomodel = VcmlReader.biomodel_from_file(vcml_source=vcml_field_data_demo_path)
    assert bio_model.model is not None
    parameters: list[ModelParameter] = bio_model.model.model_parameters
    assert {p.name: p.value for p in parameters} == {}

    sim_name = bio_model.applications[0].simulations[0].name
    simulation_orig = VcmlSpatialSimulation(bio_model=bio_model, out_dir=sim_dir)
    # # create a temporary file to write the VCML content to
    # vcml_path = Path(tempfile.mktemp(prefix="model_", suffix=".xml"))
    # vcml_spatial_model.export(vcml_path)
    results_orig: Result = simulation_orig.run(simulation_name=sim_name)

    channels_orig = results_orig.channel_data
    assert [channel.label for channel in channels_orig] == [
        "region_mask",
        "t",
        "x",
        "y",
        "z",
        "species0_cyt",
        "species0_ec",
    ]
    # assert np.allclose(
    #     results_orig.concentrations[0, 0::10],
    #     np.array(
    #         [500000.00000000006, 236185.00811512678, 111567.6111715472],
    #         dtype=np.float64,
    #     ),
    # )
