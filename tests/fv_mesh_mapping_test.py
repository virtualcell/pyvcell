from pathlib import Path

from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.vtk.fv_mesh_mapping import from_mesh3d_membrane, from_mesh3d_volume
from pyvcell.simdata.vtk.vtkmesh_fv import write_finite_volume_smoothed_vtk_grid_and_index_data
from tests.test_fixture import setup_files, teardown_files

test_data_dir = (Path(__file__).parent / "test_data").absolute()


def test_mesh_parse() -> None:
    setup_files()

    mesh = CartesianMesh(mesh_file=test_data_dir / "SimID_946368938_0_.mesh")
    mesh.read()

    plasma_membrane_vismesh = from_mesh3d_membrane(mesh, {0, 1, 2, 3})
    assert plasma_membrane_vismesh.dimension == 3

    cytosol_vismesh = from_mesh3d_volume(mesh, "cytosol")
    assert cytosol_vismesh.dimension == 3

    write_finite_volume_smoothed_vtk_grid_and_index_data(
        plasma_membrane_vismesh,
        "plasma_membrane",
        test_data_dir / "plasma_membrane.vtu",
        test_data_dir / "plasma_membrane.json",
    )
    write_finite_volume_smoothed_vtk_grid_and_index_data(
        cytosol_vismesh, "cytosol", test_data_dir / "cytosol.vtu", test_data_dir / "cytosol.json"
    )
    if (test_data_dir / "plasma_membrane.json").exists():
        (test_data_dir / "plasma_membrane.json").unlink()
    if (test_data_dir / "cytosol.json").exists():
        (test_data_dir / "cytosol.json").unlink()

    teardown_files()
