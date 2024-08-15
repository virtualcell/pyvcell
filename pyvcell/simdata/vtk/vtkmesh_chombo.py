from copy import deepcopy
from pathlib import Path

import orjson
import vtkmodules.all as vtk

from pyvcell.simdata.vtk.vismesh import ChomboIndexData, VisLine, VisMesh, VisPolygon, VisTetrahedron
from pyvcell.simdata.vtk.vtkmesh_utils import create_tetrahedra, get_membrane_vtk_grid, get_volume_vtk_grid, writevtk


def write_chombo_volume_vtk_grid_and_index_data(
    vis_mesh: VisMesh, domainname: str, vtkfile: Path, indexfile: Path
) -> None:
    original_vis_mesh = vis_mesh
    corrected_vis_mesh = original_vis_mesh  # same mesh if no irregularPolyhedra
    if original_vis_mesh.irregularPolyhedra is not None:
        corrected_vis_mesh = deepcopy(vis_mesh)
        if corrected_vis_mesh.tetrahedra is None:
            corrected_vis_mesh.tetrahedra = []
        if corrected_vis_mesh.irregularPolyhedra is None:
            raise ValueError("corrected_vis_mesh.irregularPolyhedra is None")
        for irregularPolyhedron in corrected_vis_mesh.irregularPolyhedra:
            tets = create_tetrahedra(irregularPolyhedron, corrected_vis_mesh)
            for tet in tets:
                corrected_vis_mesh.tetrahedra.append(tet)
        corrected_vis_mesh.irregularPolyhedra = None

    vtkgrid: vtk.vtkUnstructuredGrid = get_volume_vtk_grid(corrected_vis_mesh)
    writevtk(vtkgrid, vtkfile)
    chombo_index_data = ChomboIndexData(domainName=domainname)
    chombo_index_data.chomboVolumeIndices = []
    chombo_index_data.domainName = domainname
    if corrected_vis_mesh.dimension == 2:
        if corrected_vis_mesh.polygons is not None:
            for polygon in corrected_vis_mesh.polygons:
                if not isinstance(polygon, VisPolygon):
                    raise TypeError(f"expected VisPolygon but got {type(polygon)}")
                if polygon.chomboVolumeIndex is None:
                    raise ValueError("polygon.chomboVolumeIndex is None")
                chombo_index_data.chomboVolumeIndices.append(polygon.chomboVolumeIndex)
        if chombo_index_data.chomboVolumeIndices is None:
            print("didn't find any indices ... bad")
    elif corrected_vis_mesh.dimension == 3:
        if corrected_vis_mesh.visVoxels is not None:
            for voxel in corrected_vis_mesh.visVoxels:
                if voxel.chomboVolumeIndex is None:
                    raise ValueError("voxel.chomboVolumeIndex is None")
                chombo_index_data.chomboVolumeIndices.append(voxel.chomboVolumeIndex)
        if corrected_vis_mesh.irregularPolyhedra is not None:
            raise ValueError("unexpected irregular polyhedra in mesh, should have been replaced with tetrahedra")
        if corrected_vis_mesh.tetrahedra is not None:
            for tetrahedron in corrected_vis_mesh.tetrahedra:
                if not isinstance(tetrahedron, VisTetrahedron):
                    raise TypeError(f"expected VisTetrahedron but got {type(tetrahedron)}")
                if tetrahedron.chomboVolumeIndex is None:
                    raise ValueError("tetrahedron.chomboVolumeIndex is None")
                chombo_index_data.chomboVolumeIndices.append(tetrahedron.chomboVolumeIndex)
        if len(chombo_index_data.chomboVolumeIndices) == 0:
            print("didn't find any indices ... bad")
    write_chombo_index_data(indexfile, chombo_index_data)


def write_chombo_membrane_vtk_grid_and_index_data(
    vis_mesh: VisMesh, domainname: str, vtkfile: Path, indexfile: Path
) -> None:
    vtkgrid = get_membrane_vtk_grid(vis_mesh)
    writevtk(vtkgrid, vtkfile)

    chombo_index_data = ChomboIndexData(domainName=domainname)
    chombo_index_data.chomboSurfaceIndices = []
    if domainname.upper().endswith("MEMBRANE") is False:
        raise ValueError("expecting domain name ending with membrane")
    chombo_index_data.domainName = domainname
    if vis_mesh.dimension == 3:
        if vis_mesh.surfaceTriangles is not None:
            for surfaceTriangle in vis_mesh.surfaceTriangles:
                if surfaceTriangle.chomboSurfaceIndex is None:
                    raise ValueError("surfaceTriangle.chomboSurfaceIndex is None")
                chombo_index_data.chomboSurfaceIndices.append(surfaceTriangle.chomboSurfaceIndex)
    elif vis_mesh.dimension == 2:
        if vis_mesh.visLines is not None:
            for visLine in vis_mesh.visLines:
                if not isinstance(visLine, VisLine):
                    raise TypeError(f"expected VisLine but got {type(visLine)}")
                if visLine.chomboSurfaceIndex is None:
                    raise ValueError("visLine.chomboSurfaceIndex is None")
                chombo_index_data.chomboSurfaceIndices.append(visLine.chomboSurfaceIndex)
    else:
        raise ValueError(f"unexpected mesh dimension {vis_mesh.dimension}")
    if len(chombo_index_data.chomboSurfaceIndices) == 0:
        print("didn't find any indices ... bad")
    write_chombo_index_data(indexfile, chombo_index_data)


def write_chombo_index_data(chombo_index_file: Path, chombo_index_data: ChomboIndexData) -> None:
    json = orjson.dumps(chombo_index_data, option=orjson.OPT_NAIVE_UTC | orjson.OPT_SERIALIZE_NUMPY)
    with chombo_index_file.open("wb") as ff:
        ff.write(json)
