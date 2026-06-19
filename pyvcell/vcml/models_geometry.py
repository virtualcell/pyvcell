"""Data model for VCell geometry definitions.

These types describe a geometry on its own terms — extent/origin, image data,
subvolumes (analytic / image / CSG), and surface classes — independent of any
biomodel. Application-level structure mapping (which structure maps to which
geometry class) belongs with the biomodel in ``models.py``; it is intentionally
not here. Keeping geometry separate lets math-only / geometry-only third-party
packages depend on it without pulling in biomodel constructs.
"""

import zlib
from typing import TYPE_CHECKING

import numpy as np
from pydantic import Field

from pyvcell._internal.geometry.segmented_image_geometry import (
    SegmentedImageGeometry,
    _evaluate_analytic_expr,
)
from pyvcell.sim_results.var_types import NDArray3Du8
from pyvcell.vcml.models_base import StrEnum, VcmlNode

if TYPE_CHECKING:
    from pyvcell._internal.simdata.mesh import CartesianMesh


class PixelClass(VcmlNode):
    name: str
    pixel_value: int


class Image(VcmlNode):
    name: str
    size: tuple[int, int, int]
    uncompressed_size: int
    compressed_content: str
    pixel_classes: list[PixelClass] = Field(default_factory=list)

    @property
    def ndarray_3d_u8(self) -> NDArray3Du8:
        """Decompress and return the image as a ``(Z, Y, X)`` uint8 array."""
        compressed_bytes = bytes.fromhex(self.compressed_content)
        raw_pixels = zlib.decompress(compressed_bytes)
        # size is (X, Y, Z); pixel data is X-fastest → reshape to (Z, Y, X)
        sx, sy, sz = self.size
        return np.frombuffer(raw_pixels, dtype=np.uint8).astype(np.uint8).reshape((sz, sy, sx))

    @staticmethod
    def from_ndarray_3d_u8(ndarray_3d_u8: NDArray3Du8, name: str) -> "Image":
        """Create an Image from a ``(Z, Y, X)`` uint8 numpy array."""
        # Input shape is (Z, Y, X); store size as (X, Y, Z) per VCell convention
        nz, ny, nx = ndarray_3d_u8.shape
        size: tuple[int, int, int] = (nx, ny, nz)

        unique_values = np.unique(ndarray_3d_u8)
        pixel_classes: list[PixelClass] = []
        for value in unique_values:
            pixel_class = PixelClass(name=f"class_{value!s}", pixel_value=value)
            pixel_classes.append(pixel_class)

        # C-order flatten of (Z, Y, X) array gives X-fastest byte order
        raw_pixels: bytes = ndarray_3d_u8.flatten().tobytes()
        compressed_bytes: bytes = zlib.compress(raw_pixels)
        return Image(
            name=name,
            size=size,
            uncompressed_size=len(raw_pixels),
            compressed_content=compressed_bytes.hex(),
            pixel_classes=pixel_classes,
        )


class SubVolumeType(StrEnum):
    analytic = "analytic"
    csg = "csg"
    image = "image"
    compartmental = "compartmental"

    def to_xml(self) -> str:
        if self == SubVolumeType.analytic:
            return "Analytical"
        elif self == SubVolumeType.csg:
            return "CSGGeometry"
        elif self == SubVolumeType.image:
            return "Image"
        elif self == SubVolumeType.compartmental:
            return "Compartmental"
        else:
            raise ValueError(f"Unknown SubVolumeType: {self}")


class GeometryClass(VcmlNode):
    name: str


class SubVolume(GeometryClass):
    handle: int
    subvolume_type: SubVolumeType
    analytic_expr: str | None = None
    image_pixel_value: int | None = None


class SurfaceClass(GeometryClass):
    subvolume_ref_1: str
    subvolume_ref_2: str


class Geometry(VcmlNode):
    name: str
    dim: int = 0
    extent: tuple[float, float, float] = (1.0, 1.0, 1.0)
    origin: tuple[float, float, float] = (1.0, 1.0, 1.0)
    image: Image | None = None
    subvolumes: list[SubVolume] = Field(default_factory=list)
    surface_classes: list[SurfaceClass] = Field(default_factory=list)

    def add_background(self, name: str) -> SubVolume:
        sub_volume = SubVolume(
            name=name, handle=len(self.subvolumes), subvolume_type=SubVolumeType.analytic, analytic_expr="1.0"
        )
        self.subvolumes.append(sub_volume)
        return sub_volume

    def add_sphere(self, name: str, radius: float, center: tuple[float, float, float]) -> SubVolume:
        expr = f"(pow(x-{center[0]},2.0) + pow(y-{center[1]},2.0) + pow(z-{center[2]},2.0)) < pow({radius},2.0)"
        sub_volume = SubVolume(
            name=name, handle=len(self.subvolumes), subvolume_type=SubVolumeType.analytic, analytic_expr=expr
        )
        self.subvolumes.append(sub_volume)
        return sub_volume

    def add_surface(self, name: str, sub_volume_1: SubVolume | str, sub_volume_2: SubVolume | str) -> SurfaceClass:
        sub_volume_1_name = sub_volume_1.name if isinstance(sub_volume_1, SubVolume) else sub_volume_1
        sub_volume_2_name = sub_volume_2.name if isinstance(sub_volume_2, SubVolume) else sub_volume_2
        surface_class = SurfaceClass(name=name, subvolume_ref_1=sub_volume_1_name, subvolume_ref_2=sub_volume_2_name)
        self.surface_classes.append(surface_class)
        return surface_class

    def to_segmented_image(self, resolution: int = 50) -> SegmentedImageGeometry:
        """Build a :class:`SegmentedImageGeometry` from this geometry.

        Args:
            resolution: Number of grid points along each axis (analytic geometries only).
        """
        ox, oy, oz = self.origin
        ex, ey, ez = self.extent

        if self.image is not None:
            compressed_bytes = bytes.fromhex(self.image.compressed_content)
            raw_pixels = zlib.decompress(compressed_bytes)
            # image.size is (X, Y, Z); pixel data is X-fastest, so reshape to (Z, Y, X)
            sx, sy, sz = self.image.size
            label_array = (
                np.frombuffer(raw_pixels, dtype=np.uint8)
                .astype(np.int32)
                .reshape((sz, sy, sx))  # [z, y, x]
                .transpose((2, 1, 0))  # [x, y, z] = (nx, ny, nz)
            )
            # Map pixel values to subvolume names (subvolumes have image_pixel_value matching pixel classes)
            pixel_to_subvolume = {
                sv.image_pixel_value: sv.name for sv in self.subvolumes if sv.image_pixel_value is not None
            }
            label_names = {
                pv: pixel_to_subvolume.get(pv, pc_name)
                for pv, pc_name in ((pc.pixel_value, pc.name) for pc in self.image.pixel_classes)
            }
        else:
            nx = ny = nz = resolution
            x = np.linspace(ox + ex / (2 * nx), ox + ex - ex / (2 * nx), nx)
            y = np.linspace(oy + ey / (2 * ny), oy + ey - ey / (2 * ny), ny)
            z = np.linspace(oz + ez / (2 * nz), oz + ez - ez / (2 * nz), nz)
            x3d, y3d, z3d = np.meshgrid(x, y, z, indexing="ij")

            label_array = np.zeros((nx, ny, nz), dtype=np.int32)
            # Iterate in reverse so earlier subvolumes (higher priority) win
            for idx, sv in reversed(list(enumerate(self.subvolumes))):
                if sv.analytic_expr is None:
                    continue
                mask = _evaluate_analytic_expr(sv.analytic_expr, x3d, y3d, z3d)
                label_array[mask > 0] = idx
            label_names = {idx: sv.name for idx, sv in enumerate(self.subvolumes)}

        spacing = (ex / label_array.shape[0], ey / label_array.shape[1], ez / label_array.shape[2])
        return SegmentedImageGeometry(
            labels=label_array,
            origin=(ox, oy, oz),
            spacing=spacing,
            label_names=label_names,
        )

    def plot(self, resolution: int = 50, save_path: str | None = None) -> None:
        """Render the geometry using PyVista.

        Args:
            resolution: Number of grid points along each axis.
            save_path: If provided, save the figure to this path before showing.
        """
        self.to_segmented_image(resolution=resolution).plot(save_path=save_path)

    @property
    def subvolume_names(self) -> list[str]:
        return [subvolume.name for subvolume in self.subvolumes]

    @property
    def surface_class_names(self) -> list[str]:
        return [surface_class.name for surface_class in self.surface_classes]

    def to_cartesian_mesh(self, mesh_size: tuple[int, int, int] | None = None, resolution: int = 50) -> "CartesianMesh":
        """Generate the VCell finite-volume :class:`CartesianMesh` for this geometry.

        Convenience wrapper around :func:`pyvcell.vcml.cartesian_mesh_from_geometry`;
        requires the ``native`` and ``solver`` extras (libvcell + pyvcell-fvsolver).
        """
        from pyvcell.vcml.vcml_simulation import cartesian_mesh_from_geometry

        return cartesian_mesh_from_geometry(self, mesh_size=mesh_size, resolution=resolution)
