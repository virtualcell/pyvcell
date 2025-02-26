import os
from pathlib import Path

import pytest
import pyvista

from pyvcell.data_model.result import Result
from pyvcell.data_model.var_types import NDArray1D
from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.vtk.fv_mesh_mapping import from_mesh_data
from pyvcell.simdata.vtk.vismesh import FiniteVolumeIndex, FiniteVolumeIndexData, VisMesh
from pyvcell.simdata.vtk.vtkmesh_fv import (
    write_finite_volume_index_data,
    write_finite_volume_smoothed_vtk_grid_and_index_data,
)
from pyvcell.simdata.vtk.vtkmesh_utils import write_data_array_to_new_vtk_file

pyvista.OFF_SCREEN = True


IN_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"


@pytest.mark.skipif(IN_GITHUB_ACTIONS, reason="Test doesn't work in Github Actions.")
def test_vtk(solver_output_path: Path, solver_output_simid_jobid: tuple[int, int], zarr_path: Path) -> None:
    sim_id, job_id = solver_output_simid_jobid
    result = Result(solver_output_dir=solver_output_path, sim_id=sim_id, job_id=job_id, zarr_dir=zarr_path)
    mesh: CartesianMesh = result.mesh
    domain_names: list[str] = mesh.get_volume_domain_names()
    assert domain_names == ["Nucleus", "cytosol", "ec"]
    channel_names = [c.label for c in result.channels]
    assert channel_names == ["C_cyt", "Ran_cyt", "RanC_cyt", "RanC_nuc", "J_r0"]
    times: list[float] = result.get_times()
    assert times == [0.0, 0.25, 0.5, 0.75, 1.0]

    domain_name = domain_names[0]

    vis_mesh: VisMesh = from_mesh_data(cartesian_mesh=mesh, domain_name=domain_name, b_volume=True)

    assert vis_mesh.visVoxels is not None
    finite_volume_indices: list[FiniteVolumeIndex] = [
        vox.finiteVolumeIndex for vox in vis_mesh.visVoxels if vox.finiteVolumeIndex is not None
    ]
    finite_volume_index_data: FiniteVolumeIndexData = FiniteVolumeIndexData(
        domainName=domain_name, finiteVolumeIndices=finite_volume_indices
    )
    empty_mesh_file: Path = Path(f"empty_mesh_{domain_name}.vtu")
    index_file: Path = Path(f"index_file_{domain_name}.json")
    assert empty_mesh_file.name == "empty_mesh_Nucleus.vtu"
    assert index_file.name == "index_file_Nucleus.json"
    write_finite_volume_index_data(
        finite_volume_index_file=index_file, finite_volume_index_data=finite_volume_index_data
    )

    write_finite_volume_smoothed_vtk_grid_and_index_data(
        vis_mesh=vis_mesh, domain_name=domain_name, vtu_file=empty_mesh_file, index_file=index_file
    )

    var_name = "Nucleus::RanC_nuc"
    simple_var_name = var_name.split("::")[-1]
    time: float = times[0]
    data_array: NDArray1D = result.pde_dataset.get_data(var_name, time)
    new_mesh_file: Path = Path(f"mesh_{domain_name}_{simple_var_name}_{time}.vtu")
    assert new_mesh_file.name == "mesh_Nucleus_RanC_nuc_0.0.vtu"
    write_data_array_to_new_vtk_file(
        empty_mesh_file=empty_mesh_file, var_name=var_name, data=data_array, new_mesh_file=new_mesh_file
    )

    # plot with pyvista
    pyvista_mesh = pyvista.read(str(new_mesh_file))
    # pyvista_mesh.plot()
    plotter = pyvista.Plotter(off_screen=True)
    plotter.add_mesh(pyvista_mesh)
    plotter.screenshot(f"mesh_{domain_name}_{simple_var_name}_{time}.png")
    plotter.close()
