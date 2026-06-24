"""Result of a moving-boundary simulation.

Unlike the finite-volume solver, the moving-boundary solver does not write a
fixed Cartesian grid. Its solution lives on a mesh that moves with the boundary,
so a result is a time series of frames, where each frame carries the moving
front (a polygon of ``(x, y)`` points) and the field values of the "inside"
mesh elements at that time. This mirrors VCell's own moving-boundary data model
(elements + per-species values on the moving mesh), rather than the
zarr/4-D Cartesian :class:`~pyvcell.sim_results.result.Result`.

These objects hold only numpy arrays and plain Python, so they can be inspected
and post-processed without any heavy optional dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class MovingBoundaryFrame:
    """A single output time step of a moving-boundary simulation.

    Attributes:
        time: the simulation time of this frame.
        front: ``(N, 2)`` array of the moving-front boundary polygon ``(x, y)``.
        x, y: ``(M,)`` coordinates of the inside mesh elements.
        grid_i, grid_j: ``(M,)`` integer grid indices of the inside elements.
        concentrations: species name -> ``(M,)`` array of element concentrations,
            aligned with ``x``/``y``/``grid_i``/``grid_j``.
    """

    time: float
    front: np.ndarray
    x: np.ndarray
    y: np.ndarray
    grid_i: np.ndarray
    grid_j: np.ndarray
    concentrations: dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class MovingBoundaryResult:
    """The full time series of a moving-boundary simulation.

    Attributes:
        species_names: the volume species, in the same order the solver reports
            concentrations.
        frames: the output-time frames, in increasing time order.
    """

    species_names: list[str]
    frames: list[MovingBoundaryFrame] = field(default_factory=list)

    @property
    def times(self) -> np.ndarray:
        """The output times as a 1-D array."""
        return np.array([frame.time for frame in self.frames], dtype=float)

    def front(self, time_index: int) -> np.ndarray:
        """The moving-front polygon ``(N, 2)`` at the given output index."""
        return self.frames[time_index].front

    def concentrations(self, species_name: str, time_index: int) -> np.ndarray:
        """Inside-element concentrations of ``species_name`` at the given output index."""
        return self.frames[time_index].concentrations[species_name]

    def __repr__(self) -> str:
        n = len(self.frames)
        span = f"{self.frames[0].time:g}..{self.frames[-1].time:g}" if n else "empty"
        return f"MovingBoundaryResult(species={self.species_names}, frames={n}, t={span})"
