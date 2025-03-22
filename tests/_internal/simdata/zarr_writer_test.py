from pathlib import Path

from pyvcell._internal.simdata.mesh import CartesianMesh
from pyvcell._internal.simdata.simdata_models import DataFunctions, PdeDataSet
from pyvcell._internal.simdata.zarr_writer import write_zarr


def test_zarr_writer(temp_sim_946368938_path: Path) -> None:
    sim_id = 946368938
    job_id = 0
    pde_dataset = PdeDataSet(base_dir=temp_sim_946368938_path, log_filename=f"SimID_{sim_id}_{job_id}_.log")
    pde_dataset.read()
    data_functions = DataFunctions(function_file=temp_sim_946368938_path / f"SimID_{sim_id}_{job_id}_.functions")
    data_functions.read()
    mesh = CartesianMesh(mesh_file=temp_sim_946368938_path / f"SimID_{sim_id}_{job_id}_.mesh")
    mesh.read()

    write_zarr(
        pde_dataset=pde_dataset, data_functions=data_functions, mesh=mesh, zarr_dir=temp_sim_946368938_path / "zarr"
    )

    # TODO: verify the written data
