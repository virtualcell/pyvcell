"""Generate a CartesianMesh directly from a Geometry (no full model needed)."""

import pyvcell.vcml as vc
from pyvcell._internal.simdata.mesh import CartesianMesh


def _two_region_geometry(dim: int, extent: tuple[float, float, float]) -> vc.Geometry:
    """A sphere/circle subdomain inside a background, with a separating membrane.

    The region-defining subvolume is added before the background so it wins
    (earlier subvolumes have higher priority).
    """
    geo = vc.Geometry(name="g", dim=dim, extent=extent, origin=(0.0, 0.0, 0.0))
    center = (extent[0] / 2, extent[1] / 2, extent[2] / 2 if dim == 3 else 0.0)
    geo.add_sphere("cell", radius=2.0, center=center)
    geo.add_background("bg")
    geo.add_surface("cell_bg_membrane", "cell", "bg")
    return geo


def test_cartesian_mesh_from_geometry_3d() -> None:
    geo = _two_region_geometry(3, (8.0, 8.0, 8.0))
    mesh = vc.cartesian_mesh_from_geometry(geo, mesh_size=(12, 12, 12))

    assert isinstance(mesh, CartesianMesh)
    assert mesh.size == [12, 12, 12]
    assert mesh.extent == [8.0, 8.0, 8.0]
    assert mesh.origin == [0.0, 0.0, 0.0]
    assert mesh.dimension == 3
    assert {region[3] for region in mesh.volume_regions} == {"bg", "cell"}
    assert len(mesh.membrane_regions) >= 1


def test_geometry_to_cartesian_mesh_2d() -> None:
    geo = _two_region_geometry(2, (8.0, 8.0, 1.0))
    mesh = geo.to_cartesian_mesh(mesh_size=(16, 16, 1))

    assert mesh.size == [16, 16, 1]
    assert mesh.dimension == 2
    assert {region[3] for region in mesh.volume_regions} == {"bg", "cell"}


def test_default_mesh_size_uses_resolution() -> None:
    geo = _two_region_geometry(3, (8.0, 8.0, 8.0))
    mesh = geo.to_cartesian_mesh(resolution=10)
    assert mesh.size == [10, 10, 10]
