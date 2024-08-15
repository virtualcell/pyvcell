from pathlib import Path

import orjson

from pyvcell.simdata.vtk.vismesh import MovingBoundaryIndexData, VisMesh
from pyvcell.simdata.vtk.vtkmesh_utils import get_volume_vtk_grid, writevtk


def write_moving_boundary_volume_vtk_grid_and_index_data(
    vis_mesh: VisMesh, domain_name: str, vtu_file: Path, index_file: Path
) -> None:
    vtkgrid = get_volume_vtk_grid(vis_mesh)
    writevtk(vtkgrid, vtu_file)
    moving_boundary_index_data = MovingBoundaryIndexData(domainName=domain_name, timeIndex=0)
    moving_boundary_index_data.movingBoundaryVolumeIndices = []
    if vis_mesh.dimension == 2:
        # if volume
        if vis_mesh.polygons is not None:
            for polygon in vis_mesh.polygons:
                if polygon.movingBoundaryVolumeIndex is None:
                    raise ValueError("polygon.movingBoundaryVolumeIndex is None")
                moving_boundary_index_data.movingBoundaryVolumeIndices.append(polygon.movingBoundaryVolumeIndex)
        # if membrane
        if vis_mesh.visLines is not None:
            for visLine in vis_mesh.visLines:
                if visLine.movingBoundarySurfaceIndex is None:
                    raise ValueError("visLine.movingBoundarySurfaceIndex is None")
                if moving_boundary_index_data.movingBoundarySurfaceIndices is None:
                    raise ValueError("moving_boundary_index_data.movingBoundarySurfaceIndices is None")
                moving_boundary_index_data.movingBoundarySurfaceIndices.append(visLine.movingBoundarySurfaceIndex)
    # elif visMesh.dimension == 3:
    #     # if volume
    #     if visMesh.visVoxels is not None:
    #         for voxel in visMesh.visVoxels:
    #             moving_boundary_index_data.finiteVolumeIndices.append(voxel.finiteVolumeIndex)
    #     if visMesh.irregularPolyhedra is not None:
    #         raise Exception("unexpected irregular polyhedra in mesh, should have been replaced with tetrahedra")
    #     if visMesh.tetrahedra is not None:
    #         for tetrahedron in visMesh.tetrahedra:
    #             moving_boundary_index_data.finiteVolumeIndices.append(tetrahedron.finiteVolumeIndex)
    #     # if membrane
    #     if visMesh.polygons is not None:
    #         for polygon in visMesh.polygons:
    #             moving_boundary_index_data.finiteVolumeIndices.append(polygon.finiteVolumeIndex)

    if (
        moving_boundary_index_data.movingBoundaryVolumeIndices is None
        and moving_boundary_index_data.movingBoundarySurfaceIndices is None
    ):
        print("didn't find any indices ... bad")

    if (
        moving_boundary_index_data.movingBoundaryVolumeIndices is not None
        and len(moving_boundary_index_data.movingBoundaryVolumeIndices) == 0
    ):
        print("didn't find any indices ... bad")

    if (
        moving_boundary_index_data.movingBoundarySurfaceIndices is not None
        and len(moving_boundary_index_data.movingBoundarySurfaceIndices) == 0
    ):
        print("didn't find any indices ... bad")

    write_moving_boundary_index_data(index_file, moving_boundary_index_data)


def write_moving_boundary_index_data(
    moving_boundary_index_file: Path, moving_boundary_index_data: MovingBoundaryIndexData
) -> None:
    json = orjson.dumps(moving_boundary_index_data, option=orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY)
    with moving_boundary_index_file.open("wb") as ff:
        ff.write(json)
