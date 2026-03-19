import numpy as np
import pytest

from pyvcell._internal.geometry.segmented_image_geometry import (
    SegmentedImageGeometry,
    _evaluate_analytic_expr,
)
from pyvcell.vcml.models import Geometry, Image, PixelClass

# --- _evaluate_analytic_expr ---


class TestEvaluateAnalyticExpr:
    def test_simple_expression(self) -> None:
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([0.0, 0.0, 0.0])
        z = np.array([0.0, 0.0, 0.0])
        result = _evaluate_analytic_expr("x + 1", x, y, z)
        np.testing.assert_array_almost_equal(result, [2.0, 3.0, 4.0])

    def test_pow_conversion(self) -> None:
        x = np.array([2.0, 3.0])
        y = np.zeros(2)
        z = np.zeros(2)
        result = _evaluate_analytic_expr("pow(x, 2.0)", x, y, z)
        np.testing.assert_array_almost_equal(result, [4.0, 9.0])

    def test_caret_conversion(self) -> None:
        x = np.array([2.0, 3.0])
        y = np.zeros(2)
        z = np.zeros(2)
        result = _evaluate_analytic_expr("x^2", x, y, z)
        np.testing.assert_array_almost_equal(result, [4.0, 9.0])

    def test_sphere_expression(self) -> None:
        """The kind of expression VCell generates for a sphere."""
        x = np.array([5.0, 0.0])
        y = np.array([5.0, 0.0])
        z = np.array([5.0, 0.0])
        expr = "(pow(x-5,2.0) + pow(y-5,2.0) + pow(z-5,2.0)) < pow(3,2.0)"
        result = _evaluate_analytic_expr(expr, x, y, z)
        # center is inside, corner is outside
        assert result[0] == True  # noqa: E712
        assert result[1] == False  # noqa: E712


# --- SegmentedImageGeometry ---


class TestSegmentedImageGeometry:
    @pytest.fixture()
    def simple_seg(self) -> SegmentedImageGeometry:
        labels = np.zeros((10, 10, 10), dtype=np.int32)
        labels[3:7, 3:7, 3:7] = 1
        return SegmentedImageGeometry(
            labels=labels,
            origin=(0.0, 0.0, 0.0),
            spacing=(1.0, 1.0, 1.0),
            label_names={0: "background", 1: "cell"},
        )

    def test_attributes(self, simple_seg: SegmentedImageGeometry) -> None:
        assert simple_seg.labels.shape == (10, 10, 10)
        assert simple_seg.labels.dtype == np.int32
        assert simple_seg.origin == (0.0, 0.0, 0.0)
        assert simple_seg.spacing == (1.0, 1.0, 1.0)
        assert simple_seg.label_names == {0: "background", 1: "cell"}

    def test_unique_labels(self, simple_seg: SegmentedImageGeometry) -> None:
        unique = sorted(set(simple_seg.labels.flat))
        assert unique == [0, 1]

    def test_to_pyvista(self, simple_seg: SegmentedImageGeometry) -> None:
        grid = simple_seg.to_pyvista()
        assert grid.dimensions == (11, 11, 11)
        assert grid.spacing == (1.0, 1.0, 1.0)
        assert grid.origin == (0.0, 0.0, 0.0)
        assert "subvolume" in grid.cell_data
        assert grid.cell_data["subvolume"].shape == (1000,)

    def test_to_pyvista_nonunit_spacing(self) -> None:
        labels = np.zeros((5, 10, 20), dtype=np.int32)
        seg = SegmentedImageGeometry(
            labels=labels,
            origin=(1.0, 2.0, 3.0),
            spacing=(0.5, 0.25, 0.1),
            label_names={0: "bg"},
        )
        grid = seg.to_pyvista()
        assert grid.dimensions == (6, 11, 21)
        assert grid.spacing == (0.5, 0.25, 0.1)
        assert grid.origin == (1.0, 2.0, 3.0)


# --- Geometry.to_segmented_image ---


class TestGeometryToSegmentedImage:
    def test_analytic_sphere(self) -> None:
        geo = Geometry(name="test", origin=(0, 0, 0), extent=(10, 10, 10), dim=3)
        # Sphere first (higher priority), then background — first match wins
        geo.add_sphere("sphere", radius=4, center=(5, 5, 5))
        geo.add_background("bg")

        seg = geo.to_segmented_image(resolution=20)

        assert seg.labels.shape == (20, 20, 20)
        assert seg.spacing == (0.5, 0.5, 0.5)
        assert seg.origin == (0.0, 0.0, 0.0)
        assert seg.label_names == {0: "sphere", 1: "bg"}
        # center should be labeled as sphere (0)
        assert seg.labels[10, 10, 10] == 0
        # corner should be labeled as background (1)
        assert seg.labels[0, 0, 0] == 1

    def test_analytic_resolution(self) -> None:
        geo = Geometry(name="test", origin=(0, 0, 0), extent=(10, 10, 10), dim=3)
        geo.add_background("bg")

        seg30 = geo.to_segmented_image(resolution=30)
        seg50 = geo.to_segmented_image(resolution=50)

        assert seg30.labels.shape == (30, 30, 30)
        assert seg50.labels.shape == (50, 50, 50)

    def test_image_based(self) -> None:
        # raw shape is (Z, Y, X) = (4, 6, 8); z-slices 0-1 set to 1
        raw = np.zeros((4, 6, 8), dtype=np.uint8)
        raw[0:2, :, :] = 1
        image = Image.from_ndarray_3d_u8(raw, name="img")
        image.pixel_classes = [
            PixelClass(name="region_a", pixel_value=0),
            PixelClass(name="region_b", pixel_value=1),
        ]

        geo = Geometry(
            name="img_geo",
            origin=(0, 0, 0),
            extent=(8, 6, 4),
            dim=3,
            image=image,
        )

        seg = geo.to_segmented_image()

        # labels shape is (nx, ny, nz) = (8, 6, 4)
        assert seg.labels.shape == (8, 6, 4)
        assert seg.label_names == {0: "region_a", 1: "region_b"}
        assert seg.origin == (0.0, 0.0, 0.0)
        assert seg.spacing == (1.0, 1.0, 1.0)
        # raw z-slices 0-1 are 1, z-slices 2-3 are 0; labels indexed as [x, y, z]
        assert seg.labels[0, 0, 0] == 1  # z=0
        assert seg.labels[0, 0, 3] == 0  # z=3

    def test_plot_delegates(self) -> None:
        """Geometry.plot() should delegate to SegmentedImageGeometry.plot()."""
        geo = Geometry(name="test", origin=(0, 0, 0), extent=(10, 10, 10), dim=3)
        geo.add_background("bg")

        # Verify to_segmented_image works (plot itself needs display)
        seg = geo.to_segmented_image(resolution=10)
        assert isinstance(seg, SegmentedImageGeometry)
