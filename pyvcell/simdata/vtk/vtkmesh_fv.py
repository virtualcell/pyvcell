from pathlib import Path

import orjson

from pyvcell.simdata.vtk.vismesh import FiniteVolumeIndexData, VisMesh
from pyvcell.simdata.vtk.vtkmesh_utils import get_volume_vtk_grid, smooth_unstructured_grid_surface, writevtk


def write_finite_volume_smoothed_vtk_grid_and_index_data(
    vis_mesh: VisMesh, domain_name: str, vtu_file: Path, index_file: Path
) -> None:
    vtkgrid = get_volume_vtk_grid(vis_mesh)
    vtkgrid_smoothed = smooth_unstructured_grid_surface(vtkgrid) if vis_mesh.dimension == 3 else vtkgrid
    writevtk(vtkgrid_smoothed, vtu_file)
    finite_volume_index_data = FiniteVolumeIndexData(domainName=domain_name, finiteVolumeIndices=[])
    if vis_mesh.dimension == 2:
        # if volume
        if vis_mesh.polygons is not None:
            for polygon in vis_mesh.polygons:
                if polygon.finiteVolumeIndex is None:
                    raise ValueError("polygon.finiteVolumeIndex is None")
                finite_volume_index_data.finiteVolumeIndices.append(polygon.finiteVolumeIndex)
        # if membrane
        if vis_mesh.visLines is not None:
            for visLine in vis_mesh.visLines:
                if visLine.finiteVolumeIndex is None:
                    raise ValueError("visLine.finiteVolumeIndex is None")
                finite_volume_index_data.finiteVolumeIndices.append(visLine.finiteVolumeIndex)
    elif vis_mesh.dimension == 3:
        # if volume
        if vis_mesh.visVoxels is not None:
            for voxel in vis_mesh.visVoxels:
                if voxel.finiteVolumeIndex is None:
                    raise ValueError("voxel.finiteVolumeIndex is None")
                finite_volume_index_data.finiteVolumeIndices.append(voxel.finiteVolumeIndex)
        if vis_mesh.irregularPolyhedra is not None:
            raise ValueError("unexpected irregular polyhedra in mesh, should have been replaced with tetrahedra")
        if vis_mesh.tetrahedra is not None:
            for tetrahedron in vis_mesh.tetrahedra:
                if tetrahedron.finiteVolumeIndex is None:
                    raise ValueError("tetrahedron.finiteVolumeIndex is None")
                finite_volume_index_data.finiteVolumeIndices.append(tetrahedron.finiteVolumeIndex)
        # if membrane
        if vis_mesh.polygons is not None:
            for polygon in vis_mesh.polygons:
                if polygon.finiteVolumeIndex is None:
                    raise ValueError("polygon.finiteVolumeIndex is None")
                finite_volume_index_data.finiteVolumeIndices.append(polygon.finiteVolumeIndex)

    if finite_volume_index_data.finiteVolumeIndices is None or len(finite_volume_index_data.finiteVolumeIndices) == 0:
        print("didn't find any indices ... bad")

    write_finite_volume_index_data(index_file, finite_volume_index_data)


def write_finite_volume_index_data(
    finite_volume_index_file: Path, finite_volume_index_data: FiniteVolumeIndexData
) -> None:
    json = orjson.dumps(finite_volume_index_data, option=orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY)
    with finite_volume_index_file.open("wb") as ff:
        ff.write(json)
