import os
from pathlib import Path
from typing import Union

import pyvista as pv
from vtkmodules.vtkCommonDataModel import vtkUnstructuredGrid

from pyvcell.data_model.var_types import NDArray1D
from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.simdata_models import PdeDataSet
from pyvcell.simdata.vtk.fv_mesh_mapping import from_mesh3d_volume
from pyvcell.simdata.vtk.vismesh import FiniteVolumeIndex, FiniteVolumeIndexData, VisMesh
from pyvcell.simdata.vtk.vtkmesh_fv import (
    write_finite_volume_index_data,
    write_finite_volume_smoothed_vtk_grid_and_index_data,
)
from pyvcell.simdata.vtk.vtkmesh_utils import (
    get_volume_vtk_grid,
    smooth_unstructured_grid_surface,
    write_data_array_to_new_vtk_file,
)


class VtkData:
    times: list[float]
    vtu_files: list[Path]
    out_dir: Path
    mesh: CartesianMesh

    def __init__(
        self,
        mesh: CartesianMesh,
        times: list[float],
        volume_variable_names: list[str],
        pde_dataset: PdeDataSet,
        out_dir: Path,
    ) -> None:
        self.times = times
        self.out_dir = out_dir
        self.mesh = mesh
        self.vtu_files = []
        domain_names: list[str] = mesh.get_volume_domain_names()

        for domain_name in domain_names:
            # vis_mesh: VisMesh = from_mesh_data(cartesian_mesh=mesh, domain_name=domain_name, b_volume=True)
            vis_mesh: VisMesh = from_mesh3d_volume(mesh, domain_name)
            if vis_mesh.visVoxels is None:
                raise ValueError("Vismesh.visVoxels is None when it shouldn't be.")

            finite_volume_indices: list[FiniteVolumeIndex] = [
                vox.finiteVolumeIndex for vox in vis_mesh.visVoxels if vox.finiteVolumeIndex is not None
            ]
            finite_volume_index_data: FiniteVolumeIndexData = FiniteVolumeIndexData(
                domainName=domain_name, finiteVolumeIndices=finite_volume_indices
            )
            empty_mesh_file: Path = Path(os.path.join(str(self.out_dir), f"empty_mesh_{domain_name}.vtu"))

            index_file: Path = Path(os.path.join(str(self.out_dir), f"index_file_{domain_name}.json"))

            write_finite_volume_index_data(
                finite_volume_index_file=index_file, finite_volume_index_data=finite_volume_index_data
            )

            write_finite_volume_smoothed_vtk_grid_and_index_data(
                vis_mesh=vis_mesh, domain_name=domain_name, vtu_file=empty_mesh_file, index_file=index_file
            )

            for var_name in volume_variable_names:
                simple_var_name = var_name.split("::")[-1]
                for t in times:
                    data_array: NDArray1D = pde_dataset.get_data(var_name, t)
                    new_mesh_file: Path = Path(
                        os.path.join(str(self.out_dir), f"mesh_{domain_name}_{simple_var_name}_{t}.vtu")
                    )

                    write_data_array_to_new_vtk_file(
                        empty_mesh_file=empty_mesh_file, var_name=var_name, data=data_array, new_mesh_file=new_mesh_file
                    )
                    self.vtu_files.append(new_mesh_file)

    def get_vis_mesh(self, domain_name: str) -> VisMesh:
        return from_mesh3d_volume(self.mesh, domain_name)

    def get_vtk_grid(self, domain_name: str) -> vtkUnstructuredGrid:
        vis_mesh: VisMesh = self.get_vis_mesh(domain_name)
        vtkgrid = get_volume_vtk_grid(vis_mesh)
        return smooth_unstructured_grid_surface(vtkgrid)

    def get_vtu_file(self, domain_name: str, simple_var_name: str, time_index: float) -> Union[Path, None]:
        for f in self.vtu_files:
            if domain_name in f.name and str(time_index) in f.name:
                return f
        return None

    def plot(self, mesh_file: Path) -> None:
        pyvista_mesh = pv.read(str(mesh_file))
        # pyvista_mesh.plot()
        plotter = pv.Plotter(off_screen=True)
        plotter.add_mesh(pyvista_mesh)
        img_fp = os.path.join(
            os.path.dirname(str(mesh_file)),
            mesh_file.name.replace(".vtu", ".png"),
        )
        plotter.screenshot(img_fp)
        plotter.close()

    def write_mesh_animation(self, mesh_file: Path, filename: Path) -> None:
        pyvista_mesh = pv.read(str(mesh_file))
        plotter = pv.Plotter(off_screen=True)
        plotter.open_movie(str(filename))
        plotter.add_mesh(pyvista_mesh)
        plotter.write_frame()

        for t in self.times:
            plotter.add_text(f"Iteration: {t}", name="time-label")
            plotter.write_frame()

        print(f"Wrote vtk animation to {filename.name}")
        plotter.close()
