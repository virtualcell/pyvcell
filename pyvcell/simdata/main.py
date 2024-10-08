from pathlib import Path

import typer

from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.simdata_models import DataFunctions, PdeDataSet
from pyvcell.simdata.zarr_writer import write_zarr

app = typer.Typer()


@app.command(name="vc_to_zarr", help="Convert a VCell FiniteVolume simulation dataset to Zarr")
def n5_to_zarr(
    sim_data_dir: Path = typer.Argument(..., help="path to vcell dataset directory"),
    sim_id: int = typer.Argument(..., help="simulation id (e.g. 946368938)"),
    job_id: int = typer.Argument(..., help="job id (e.g. 0"),
    zarr_path: Path = typer.Argument(..., help="path to zarr dataset to write to"),
) -> None:
    pde_dataset = PdeDataSet(base_dir=sim_data_dir, log_filename=f"SimID_{sim_id}_{job_id}_.log")
    pde_dataset.read()
    data_functions = DataFunctions(function_file=sim_data_dir / f"SimID_{sim_id}_{job_id}_.functions")
    data_functions.read()
    mesh = CartesianMesh(mesh_file=sim_data_dir / f"SimID_{sim_id}_{job_id}_.mesh")
    mesh.read()

    write_zarr(pde_dataset=pde_dataset, data_functions=data_functions, mesh=mesh, zarr_dir=zarr_path)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
