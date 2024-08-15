from pathlib import Path

import orjson

from pyvcell.simdata.vtk.vismesh import VisMesh, FiniteVolumeIndexData
from pyvcell.simdata.vtk.vtkmesh_utils import writevtk, get_volume_vtk_grid, smooth_unstructured_grid_surface


def write_finite_volume_smoothed_vtk_grid_and_index_data(vis_mesh: VisMesh, domain_name: str, vtu_file: Path,
                                                         index_file: Path) -> None:
    vtkgrid = get_volume_vtk_grid(vis_mesh)
    if vis_mesh.dimension == 3:
        vtkgrid_smoothed = smooth_unstructured_grid_surface(vtkgrid)
    else:
        vtkgrid_smoothed = vtkgrid
    writevtk(vtkgrid_smoothed, vtu_file)
    finite_volume_index_data = FiniteVolumeIndexData(domainName=domain_name, finiteVolumeIndices=[])
    if vis_mesh.dimension == 2:
        # if volume
        if vis_mesh.polygons is not None:
            for polygon in vis_mesh.polygons:
                assert polygon.finiteVolumeIndex is not None
                finite_volume_index_data.finiteVolumeIndices.append(polygon.finiteVolumeIndex)
        # if membrane
        if vis_mesh.visLines is not None:
            for visLine in vis_mesh.visLines:
                assert visLine.finiteVolumeIndex is not None
                finite_volume_index_data.finiteVolumeIndices.append(visLine.finiteVolumeIndex)
    elif vis_mesh.dimension == 3:
        # if volume
        if vis_mesh.visVoxels is not None:
            for voxel in vis_mesh.visVoxels:
                assert voxel.finiteVolumeIndex is not None
                finite_volume_index_data.finiteVolumeIndices.append(voxel.finiteVolumeIndex)
        if vis_mesh.irregularPolyhedra is not None:
            raise Exception("unexpected irregular polyhedra in mesh, should have been replaced with tetrahedra")
        if vis_mesh.tetrahedra is not None:
            for tetrahedron in vis_mesh.tetrahedra:
                assert tetrahedron.finiteVolumeIndex is not None
                finite_volume_index_data.finiteVolumeIndices.append(tetrahedron.finiteVolumeIndex)
        # if membrane
        if vis_mesh.polygons is not None:
            for polygon in vis_mesh.polygons:
                assert polygon.finiteVolumeIndex is not None
                finite_volume_index_data.finiteVolumeIndices.append(polygon.finiteVolumeIndex)

    if finite_volume_index_data.finiteVolumeIndices is None or len(finite_volume_index_data.finiteVolumeIndices) == 0:
        print("didn't find any indices ... bad")

    write_finite_volume_index_data(index_file, finite_volume_index_data)


def write_finite_volume_index_data(finite_volume_index_file: Path,
                                   finite_volume_index_data: FiniteVolumeIndexData) -> None:
    json = orjson.dumps(finite_volume_index_data, option=orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY)
    with finite_volume_index_file.open('wb') as ff:
        ff.write(json)
