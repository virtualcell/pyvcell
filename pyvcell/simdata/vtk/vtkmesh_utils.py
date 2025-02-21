import os
from pathlib import Path

import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.vtkCommonCore import vtkDataArray

from pyvcell.data_model.var_types import NDArray1D
from pyvcell.simdata.vtk.vismesh import PolyhedronFace, VisIrregularPolyhedron, VisMesh, VisTetrahedron


#
# read a vtkUnstructuredGrid from the XML format
#
def readvtk(vtkfile: Path, verbose: bool = False) -> vtk.vtkUnstructuredGrid:
    if not os.path.isfile(vtkfile):
        raise FileNotFoundError("unstructured grid " + str(vtkfile) + " not found")

    tester = vtk.vtkXMLFileReadTester()
    tester.SetFileName(str(vtkfile))
    if tester.TestReadFile() != 1:
        raise ValueError("expecting XML formatted VTK unstructured grid")

    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(str(vtkfile))
    reader.Update()
    vtkgrid = reader.GetOutput()
    if not isinstance(vtkgrid, vtk.vtkUnstructuredGrid):
        raise TypeError("expecting a vtkUnstructuredGrid")
    print("read from file " + str(vtkfile)) if verbose else None
    vtkgrid.BuildLinks()
    return vtkgrid


#
# write a vtkUnstructuredGrid to the XML format
#
def writevtk(vtkgrid: vtk.vtkUnstructuredGrid, filename: Path, verbose: bool = False) -> None:
    writer = vtk.vtkXMLUnstructuredGridWriter()
    b_ascii = False
    if b_ascii:
        writer.SetDataModeToAscii()
    else:
        writer.SetCompressorTypeToNone()
        writer.SetDataModeToBinary()
        writer.SetInputData(vtkgrid)
    writer.SetFileName(str(filename))
    writer.Update()
    print("wrote to file " + str(filename)) if verbose else None


#
# create a single-variable vtu file
#
def write_data_array_to_new_vtk_file(
    empty_mesh_file: Path, var_name: str, data: NDArray1D, new_mesh_file: Path
) -> None:
    data = np.array(data)
    vtk_grid = readvtk(empty_mesh_file)

    data_array: vtkDataArray = numpy_to_vtk(data)  # type: ignore[no-untyped-call]
    data_array.SetName(var_name)
    cell_data: vtk.vtkCellData = vtk_grid.GetCellData()
    cell_data.AddArray(data_array)

    #
    # write mesh and data to the file for that domain and time
    #
    writevtk(vtk_grid, new_mesh_file)


def get_membrane_vtk_grid(vis_mesh: VisMesh) -> vtk.vtkUnstructuredGrid:
    vtk_points = vtk.vtkPoints()
    if vis_mesh.surfacePoints is None:
        raise ValueError("vis_mesh.surfacePoints is None")
    for visPoint in vis_mesh.surfacePoints:
        vtk_points.InsertNextPoint(visPoint.x, visPoint.y, visPoint.z)

    vtk_grid = vtk.vtkUnstructuredGrid()
    vtk_grid.Allocate(len(vis_mesh.surfacePoints), len(vis_mesh.surfacePoints))
    vtk_grid.SetPoints(vtk_points)

    if vis_mesh.dimension == 2:
        vtk_line = vtk.vtkLine()
        line_type = vtk_line.GetCellType()

        if vis_mesh.visLines is None:
            raise ValueError("vis_mesh.visLines is None")
        for line in vis_mesh.visLines:
            vtk_grid.InsertNextCell(line_type, 2, [line.p1, line.p2])
    else:
        vtk_triangle = vtk.vtkTriangle()
        triangle_type = vtk_triangle.GetCellType()
        if vis_mesh.surfaceTriangles is None:
            raise ValueError("vis_mesh.surfaceTriangles is None")
        for surfaceTriangle in vis_mesh.surfaceTriangles:
            # each triangle is a cell
            vtk_grid.InsertNextCell(triangle_type, 3, surfaceTriangle.pointIndices)

    vtk_grid.BuildLinks()
    return vtk_grid


def get_volume_vtk_grid(vis_mesh: VisMesh) -> vtk.vtkUnstructuredGrid:
    b_clip_polyhedra = True

    vtkpoints = vtk.vtkPoints()
    if vis_mesh.points is None:
        raise ValueError("vis_mesh.points is None")
    for visPoint in vis_mesh.points:
        vtkpoints.InsertNextPoint(visPoint.x, visPoint.y, visPoint.z)

    vtk_grid = vtk.vtkUnstructuredGrid()
    vtk_grid.Allocate(len(vis_mesh.points), len(vis_mesh.points))
    vtk_grid.SetPoints(vtkpoints)

    quad_type = vtk.vtkQuad().GetCellType()
    #  lineType = vtk.vtkLine().GetCellType()
    polygon_type = vtk.vtkPolygon().GetCellType()
    polyhedron_type = vtk.vtkPolyhedron().GetCellType()
    triangle_type = vtk.vtkTriangle().GetCellType()
    voxel_type = vtk.vtkVoxel().GetCellType()
    tetra_type = vtk.vtkTetra().GetCellType()

    if vis_mesh.polygons is not None:
        if vis_mesh.polygons is None:
            raise ValueError("vis_mesh.polygons is None")
        for vis_polygon in vis_mesh.polygons:
            polygon_points = vis_polygon.pointIndices
            num_points = len(polygon_points)
            if num_points == 4:
                vtk_grid.InsertNextCell(quad_type, num_points, polygon_points)
            elif num_points == 3:
                vtk_grid.InsertNextCell(triangle_type, num_points, polygon_points)
            else:
                vtk_grid.InsertNextCell(polygon_type, num_points, polygon_points)
    #
    # replace any VisIrregularPolyhedron with a list of VisTetrahedron
    #
    if vis_mesh.visVoxels is not None:
        if vis_mesh.visVoxels is None:
            raise ValueError("vis_mesh.visVoxels is None")
        for voxel in vis_mesh.visVoxels:
            polyhedron_points = voxel.pointIndices
            num_points = len(polyhedron_points)
            vtk_grid.InsertNextCell(voxel_type, num_points, polyhedron_points)

    if vis_mesh.tetrahedra is not None:
        if vis_mesh.tetrahedra is None:
            raise ValueError("vis_mesh.tetrahedra is None")
        for visTet in vis_mesh.tetrahedra:
            if not isinstance(visTet, VisTetrahedron):
                raise TypeError("expecting a VisTetrahedron")
            tet_points = visTet.pointIndices
            vtk_grid.InsertNextCell(tetra_type, len(tet_points), tet_points)

    b_initialized_faces = False
    if vis_mesh.irregularPolyhedra is not None:
        if vis_mesh.irregularPolyhedra is None:
            raise ValueError("vis_mesh.irregularPolyhedra is None")
        for clippedPolyhedron in vis_mesh.irregularPolyhedra:
            if b_clip_polyhedra:
                tets = create_tetrahedra(clippedPolyhedron, vis_mesh)
                for visTet in tets:
                    tet_points = visTet.pointIndices
                    vtk_grid.InsertNextCell(tetra_type, len(tet_points), tet_points)
            else:
                face_stream = get_vtk_face_stream(clippedPolyhedron)
                if b_initialized_faces is False and vtk_grid.GetNumberOfCells() > 0:
                    vtk_grid.InitializeFacesRepresentation(vtk_grid.GetNumberOfCells())
                b_initialized_faces = True
                vtk_grid.InsertNextCell(polyhedron_type, len(face_stream), face_stream)

    vtk_grid.BuildLinks()
    # vtk_grid.Squeeze()
    return vtk_grid


def get_vtk_face_stream(irregular_polyhedron: VisIrregularPolyhedron) -> list[int]:
    face_stream = [
        len(irregular_polyhedron.polyhedronFaces),
    ]
    for polyhedronFace in irregular_polyhedron.polyhedronFaces:
        face_stream.append(len(polyhedronFace.vertices))
        for v in polyhedronFace.vertices:
            face_stream.append(v)
    int_face_stream = [int(v) for v in face_stream]
    return int_face_stream


def smooth_unstructured_grid_surface(vtk_grid: vtk.vtkUnstructuredGrid) -> vtk.vtkUnstructuredGrid:
    ug_geometry_filter = vtk.vtkUnstructuredGridGeometryFilter()
    ug_geometry_filter.PassThroughPointIdsOn()
    ug_geometry_filter.MergingOff()
    ug_geometry_filter.SetInputData(vtk_grid)
    ug_geometry_filter.Update(0)
    surface_unstructured_grid: vtk.vtkUnstructuredGrid = ug_geometry_filter.GetOutput()
    original_points_ids_name = ug_geometry_filter.GetOriginalPointIdsName()

    # cell_data = surface_unstructured_grid.GetCellData()
    # num_cell_arrays = cell_data.GetNumberOfArrays()
    # for i in range(0, num_cell_arrays):
    #     print("CellArray(" + str(i) + ") '" + cell_data.GetArrayName(i) + "')")

    # point_data: vtk.vtkPointData = surface_unstructured_grid.GetPointData()
    # num_point_arrays = point_data.GetNumberOfArrays()
    # for i in range(0, num_point_arrays):
    #     point_array_name = point_data.GetArrayName(i)
    #     print("PointArray(" + str(i) + ") '" + point_array_name + "'")

    geometry_filter = vtk.vtkGeometryFilter()
    geometry_filter.SetInputData(surface_unstructured_grid)
    geometry_filter.Update(0)
    poly_data: vtk.vtkPolyData = geometry_filter.GetOutput()

    sync_filter = vtk.vtkWindowedSincPolyDataFilter()
    sync_filter.SetInputData(poly_data)
    sync_filter.SetNumberOfIterations(12)
    sync_filter.BoundarySmoothingOff()
    sync_filter.FeatureEdgeSmoothingOff()
    sync_filter.SetFeatureAngle(120.0)
    sync_filter.SetPassBand(0.05)
    sync_filter.NonManifoldSmoothingOff()
    sync_filter.NormalizeCoordinatesOn()
    sync_filter.Update(0)

    smoothed_polydata = sync_filter.GetOutput()

    smoothed_points: vtk.vtkPoints = smoothed_polydata.GetPoints()

    smoothed_point_data: vtk.vtkPointData = smoothed_polydata.GetPointData()
    point_ids_array: vtk.vtkIdTypeArray = smoothed_point_data.GetArray(original_points_ids_name)
    points_ids_array_size = point_ids_array.GetSize()
    orig_points = vtk_grid.GetPoints()
    for i in range(0, points_ids_array_size):
        point_id = point_ids_array.GetValue(i)
        smoothed_point = smoothed_points.GetPoint(i)
        orig_points.SetPoint(point_id, smoothed_point)

    return vtk_grid


def get_point_indices(irregular_polyhedron: VisIrregularPolyhedron) -> list[int]:
    if not isinstance(irregular_polyhedron, VisIrregularPolyhedron):
        raise TypeError("expecting a VisIrregularPolyhedron")
    point_indices_set = set()
    for face in irregular_polyhedron.polyhedronFaces:
        if not isinstance(face, PolyhedronFace):
            raise TypeError("expecting a PolyhedronFace")
        for pointIndex in face.vertices:
            point_indices_set.add(pointIndex)
    point_array = [int(x) for x in point_indices_set]
    return point_array


def create_tetrahedra(clipped_polyhedron: VisIrregularPolyhedron, vis_mesh: VisMesh) -> list[VisTetrahedron]:
    vtk_polydata = vtk.vtkPolyData()
    vtk_points = vtk.vtkPoints()
    polygon_type = vtk.vtkPolygon().GetCellType()
    unique_point_indices = get_point_indices(clipped_polyhedron)
    for point in unique_point_indices:
        if vis_mesh.points is None:
            raise ValueError("vis_mesh.points is None")
        vis_point = vis_mesh.points[point]
        vtk_points.InsertNextPoint(vis_point.x, vis_point.y, vis_point.z)
    vtk_polydata.Allocate(100, 100)
    vtk_polydata.SetPoints(vtk_points)

    for face in clipped_polyhedron.polyhedronFaces:
        face_id_list = []
        for visPointIndex in face.vertices:
            vtk_pointid = -1
            for i in range(0, len(unique_point_indices)):
                if unique_point_indices[i] == visPointIndex:
                    vtk_pointid = i
            face_id_list.append(vtk_pointid)
        vtk_polydata.InsertNextCell(polygon_type, len(face.vertices), face_id_list)

    delaunay_filter = vtk.vtkDelaunay3D()
    delaunay_filter.SetInputData(vtk_polydata)
    delaunay_filter.Update(0)
    delaunay_filter.SetAlpha(0.1)
    vtkgrid2: vtk.vtkUnstructuredGrid = delaunay_filter.GetOutput()
    if not isinstance(vtkgrid2, vtk.vtkUnstructuredGrid):
        raise TypeError("expecting a vtkUnstructuredGrid")

    vis_tets = []
    num_tets = vtkgrid2.GetNumberOfCells()
    if num_tets < 1:
        if len(unique_point_indices) == 4:
            vis_tet = VisTetrahedron(unique_point_indices)
            vis_tet.chomboVolumeIndex = clipped_polyhedron.chomboVolumeIndex
            vis_tet.finiteVolumeIndex = clipped_polyhedron.finiteVolumeIndex
            vis_tets.append(vis_tet)
            print("made trivial tet ... maybe inside out")
        else:
            print("found no tets, there are " + str(len(unique_point_indices)) + " unique point indices")

    # print("numFaces = "+str(vtk_polydata.GetNumberOfCells())+", num_tets = "+str(num_tets));
    for cellIndex in range(0, num_tets):
        cell = vtkgrid2.GetCell(cellIndex)
        if isinstance(cell, vtk.vtkTetra):
            vtk_tet: vtk.vtkTetra = cell
            tet_point_ids: vtk.vtkIdList = vtk_tet.GetPointIds()
            if not isinstance(tet_point_ids, vtk.vtkIdList):
                raise TypeError("expecting a vtkIdList")
            #
            # translate from vtkgrid pointids to visMesh point ids
            #
            num_points = tet_point_ids.GetNumberOfIds()
            vis_point_ids = []
            for p in range(0, num_points):
                vis_point_ids.append(unique_point_indices[tet_point_ids.GetId(p)])
            vis_tet = VisTetrahedron(vis_point_ids)
            if clipped_polyhedron.chomboVolumeIndex is not None:
                vis_tet.chomboVolumeIndex = clipped_polyhedron.chomboVolumeIndex
            if clipped_polyhedron.finiteVolumeIndex is not None:
                vis_tet.finiteVolumeIndex = clipped_polyhedron.finiteVolumeIndex
            vis_tets.append(vis_tet)
        else:
            print("ChomboMeshMapping.createTetrahedra(): expecting a tet, found a " + type(cell).__name__)

    return vis_tets
