import tarfile
import tempfile
from pathlib import Path

import pyvcell.vcml as vc
from pyvcell._internal.simdata.simdata_models import VariableType
from pyvcell.sim_results.result import Result
from pyvcell.vcml import get_workspace_dir


def test_vcml_field_data_from_sim_results(
    vcml_field_data_demo_biomodel: tuple[vc.Biomodel, vc.Simulation], vcml_field_data_tgz_archive_path: Path
) -> None:
    bio_model: vc.Biomodel = vcml_field_data_demo_biomodel[0]
    sim: vc.Simulation = vcml_field_data_demo_biomodel[1]

    # confirm the field data requirements
    refs = vc.field_data_refs(bio_model=bio_model, simulation_name=sim.name)
    assert refs == {
        ("test2_lsm_DEMO", "species0_cyt", VariableType.VOLUME, 0.5),
        ("test2_lsm_DEMO", "species0_ec", VariableType.VOLUME, 0.5),
    }

    # extract the preexisting simulation results to use for field data
    with tarfile.open(vcml_field_data_tgz_archive_path, "r:gz") as tar:
        tar.extractall(get_workspace_dir())
    data_dir = get_workspace_dir() / "test2_lsm_DEMO"
    assert data_dir.is_dir()

    results_orig: Result = vc.simulate(bio_model, sim.name)

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


def test_vcml_field_data_from_memory_arrays(
    vcml_field_data_demo_biomodel: tuple[vc.Biomodel, vc.Simulation], vcml_field_data_demo_arrays: list[vc.Field]
) -> None:
    bio_model: vc.Biomodel = vcml_field_data_demo_biomodel[0]
    sim: vc.Simulation = vcml_field_data_demo_biomodel[1]

    # confirm the field data requirements
    refs = vc.field_data_refs(bio_model=bio_model, simulation_name=sim.name)
    assert refs == {
        ("test2_lsm_DEMO", "species0_cyt", VariableType.VOLUME, 0.5),
        ("test2_lsm_DEMO", "species0_ec", VariableType.VOLUME, 0.5),
    }

    field_data_arrays: list[vc.Field] = vcml_field_data_demo_arrays

    # create a temporary parent directory with a subdirectory for simulation data and a subdirectory to extract the archive
    parent_dir = Path(tempfile.mkdtemp())
    sim_dir = parent_dir / "sim"
    sim_dir.mkdir()
    assert sim_dir.is_dir()

    results_orig: Result = vc.simulate(bio_model, sim.name, field_data_arrays)

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
    results_orig.cleanup()
