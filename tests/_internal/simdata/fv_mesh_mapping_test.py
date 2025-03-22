from pathlib import Path

from pyvcell._internal.simdata.mesh import CartesianMesh
from pyvcell._internal.simdata.vtk.fv_mesh_mapping import from_mesh3d_membrane, from_mesh3d_volume
from pyvcell._internal.simdata.vtk.vtkmesh_fv import write_finite_volume_smoothed_vtk_grid_and_index_data


def test_mesh_parse(temp_sim_946368938_path: Path) -> None:
    input_filenames = ["SimID_946368938_0_.mesh", "SimID_946368938_0_.functions"]
    # remove all files not in input_filenames
    for p in temp_sim_946368938_path.iterdir():
        if p.name not in input_filenames:
            p.unlink()

    filenames = [p.name for p in temp_sim_946368938_path.iterdir()]
    assert filenames == input_filenames

    mesh = CartesianMesh(mesh_file=temp_sim_946368938_path / "SimID_946368938_0_.mesh")
    mesh.read()

    plasma_membrane_vismesh = from_mesh3d_membrane(mesh, {0, 1, 2, 3})
    assert plasma_membrane_vismesh.dimension == 3

    cytosol_vismesh = from_mesh3d_volume(mesh, "cytosol")
    assert cytosol_vismesh.dimension == 3

    write_finite_volume_smoothed_vtk_grid_and_index_data(
        vis_mesh=plasma_membrane_vismesh,
        domain_name="plasma_membrane",
        vtu_file=temp_sim_946368938_path / "plasma_membrane.vtu",
        index_file=temp_sim_946368938_path / "plasma_membrane.json",
    )
    write_finite_volume_smoothed_vtk_grid_and_index_data(
        vis_mesh=cytosol_vismesh,
        domain_name="cytosol",
        vtu_file=temp_sim_946368938_path / "cytosol.vtu",
        index_file=temp_sim_946368938_path / "cytosol.json",
    )

    filenames = [p.name for p in temp_sim_946368938_path.iterdir()]
    assert filenames == [
        "plasma_membrane.vtu",
        "plasma_membrane.json",
        "SimID_946368938_0_.mesh",
        "cytosol.vtu",
        "cytosol.json",
        "SimID_946368938_0_.functions",
    ]
