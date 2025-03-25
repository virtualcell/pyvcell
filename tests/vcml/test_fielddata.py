import tarfile
import tempfile
from pathlib import Path

from pyvcell.sim_results.result import Result
from pyvcell.vcml import Biomodel, ModelParameter, VcmlReader
from pyvcell.vcml.vcml_simulation import VcmlSpatialSimulation


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
