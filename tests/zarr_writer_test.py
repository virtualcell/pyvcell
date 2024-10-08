import shutil
from pathlib import Path

from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.simdata_models import DataFunctions, PdeDataSet
from pyvcell.simdata.zarr_writer import write_zarr
from tests.test_fixture import setup_files, teardown_files

test_data_dir = (Path(__file__).parent / "test_data").absolute()


def test_zarr_writer() -> None:
    setup_files()

    sim_data_dir = test_data_dir
    sim_id = 946368938
    job_id = 0
    pde_dataset = PdeDataSet(base_dir=sim_data_dir, log_filename=f"SimID_{sim_id}_{job_id}_.log")
    pde_dataset.read()
    data_functions = DataFunctions(function_file=sim_data_dir / f"SimID_{sim_id}_{job_id}_.functions")
    data_functions.read()
    mesh = CartesianMesh(mesh_file=sim_data_dir / f"SimID_{sim_id}_{job_id}_.mesh")
    mesh.read()

    write_zarr(pde_dataset=pde_dataset, data_functions=data_functions, mesh=mesh, zarr_dir=test_data_dir / "zarr")

    # TODO: verify the written data

    # recursively remove files and directories from path (equivalent to rm -rf) for test_data_dir / "zarr"
    shutil.rmtree(test_data_dir / "zarr")

    teardown_files()
