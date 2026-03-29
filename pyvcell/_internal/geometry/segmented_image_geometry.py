from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numexpr as ne  # type: ignore[import-untyped]
import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    import pyvista as pv


def _evaluate_analytic_expr(
    expr: str, x: npt.NDArray[Any], y: npt.NDArray[Any], z: npt.NDArray[Any]
) -> npt.NDArray[Any]:
    """Evaluate a VCell analytic expression on coordinate arrays using numexpr."""
    # Convert pow(a,b) to (a)**(b)
    expr = re.sub(r"pow\(([^,]+),([^)]+)\)", r"(\1)**(\2)", expr)
    # Convert ^ to **
    expr = expr.replace("^", "**")
    return ne.evaluate(expr, local_dict={"x": x, "y": y, "z": z})  # type: ignore[no-any-return]


class SegmentedImageGeometry:
    """A labeled 3D numpy array with spatial metadata.

    Holds a segmented image representation of a geometry, independent of
    any visualization library.

    Attributes:
        labels: int32 array of shape (nx, ny, nz) with subvolume labels.
        origin: (ox, oy, oz) world-coordinate origin.
        spacing: (dx, dy, dz) cell size per axis.
        label_names: mapping from label value to subvolume name.
    """

    def __init__(
        self,
        labels: npt.NDArray[np.int32],
        origin: tuple[float, float, float],
        spacing: tuple[float, float, float],
        label_names: dict[int, str],
    ) -> None:
        self.labels = labels
        self.origin = origin
        self.spacing = spacing
        self.label_names = label_names

    def get_mask(self, subvolume_name: str) -> npt.NDArray[np.bool_]:
        """Return a boolean mask for the named subvolume.

        Args:
            subvolume_name: Name of the subvolume (e.g. ``"cell_domain"``).

        Returns:
            Boolean array with the same shape as :attr:`labels`.
        """
        for label, name in self.label_names.items():
            if name == subvolume_name:
                return self.labels == label  # type: ignore[no-any-return]
        available = list(self.label_names.values())
        raise ValueError(f"Subvolume '{subvolume_name}' not found. Available: {available}")

    def to_pyvista(self) -> pv.ImageData:
        """Convert to a PyVista ImageData with cell data 'subvolume'."""
        import pyvista as pv

        nx, ny, nz = self.labels.shape
        grid = pv.ImageData(
            dimensions=(nx + 1, ny + 1, nz + 1),
            spacing=self.spacing,
            origin=self.origin,
        )
        grid.cell_data["subvolume"] = self.labels.flatten(order="F")
        return grid

    def plot(self, save_path: str | Path | None = None) -> None:
        """Off-screen PyVista render displayed via matplotlib.

        Args:
            save_path: If provided, save the figure to this path before showing.
        """
        import matplotlib.pyplot as plt
        import pyvista as pv

        grid = self.to_pyvista()
        unique_labels = sorted(set(self.labels.flat))
        n_labels = len(unique_labels)
        cmap = plt.colormaps["tab10"]
        label_to_pos = {label: i for i, label in enumerate(unique_labels)}

        plotter = pv.Plotter(off_screen=True, window_size=(800, 600))
        for label in unique_labels:
            thresh = grid.threshold(value=[label - 0.5, label + 0.5], scalars="subvolume")
            color = cmap(label_to_pos[label] / max(n_labels - 1, 1))[:3]
            name = self.label_names.get(int(label), f"region_{label}")
            plotter.add_mesh(thresh, color=color, label=name, opacity=0.6)
        plotter.add_legend()
        img = plotter.screenshot(return_img=True)
        plotter.close()

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.imshow(img)
        ax.axis("off")
        ax.set_title("Geometry")
        plt.tight_layout()
        if save_path is not None:
            fig.savefig(save_path, bbox_inches="tight", dpi=150)
        plt.show()
