"""Thin wrapper around the ``pyvcell_mbsolver`` moving-boundary solver.

The solver reports its solution through observer callbacks rather than an output
file: once per internal time step it hands back the moving front geometry and
the per-element field values. :func:`solve_moving_boundary` runs the solver with
a collecting observer that snapshots those callbacks at the requested output
times into a :class:`~pyvcell.sim_results.moving_boundary_result.MovingBoundaryResult`.

Callers who need full control can use ``pyvcell_mbsolver`` directly; this wrapper
covers the common "run it and give me the trajectory" case.
"""

from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from typing import Any

import numpy as np
import pyvcell_mbsolver as mb

from pyvcell.sim_results.moving_boundary_result import MovingBoundaryFrame, MovingBoundaryResult

# Time tolerance (relative to the output step) for deciding a step has reached an
# output time; the solver advances on its own internal step, not the output step.
_OUTPUT_TIME_TOL = 1e-9


def solve_moving_boundary(
    setup_xml_file: PathLike[str] | str,
    species_names: Sequence[str],
    output_times: Sequence[float] | None = None,
) -> MovingBoundaryResult:
    """Run the moving-boundary solver on a ``MovingBoundarySetup`` XML file.

    Args:
        setup_xml_file: the ``*_mb.xml`` setup produced by
            ``libvcell.vcml_to_moving_boundary_input``.
        species_names: the volume species, in the order the solver reports
            concentrations (i.e. the order of the ``<species>`` entries in the
            setup file's ``<physiology>`` block).
        output_times: times at which to snapshot a frame. The first solver step
            at or past each requested time is kept; the final step is always
            kept. When None, every solver step is kept.

    Returns:
        a :class:`MovingBoundaryResult` with one frame per kept output time.
    """
    species = list(species_names)
    targets = sorted(float(t) for t in output_times) if output_times is not None else None
    result = MovingBoundaryResult(species_names=species)

    class _Collector(mb.SimulationObserver):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self._target_index = 0
            self._keep = False
            self._time = 0.0
            self._front: np.ndarray = np.empty((0, 2), dtype=float)
            self._buffer: list[tuple[float, float, int, int, list[float]]] = []

        def on_time(self, t: float, generation: int, last: bool, geometry: Any) -> None:
            keep = bool(last)
            if targets is None:
                keep = True
            else:
                tol = _OUTPUT_TIME_TOL * (targets[-1] - targets[0] + 1.0)
                while self._target_index < len(targets) and t + tol >= targets[self._target_index]:
                    keep = True
                    self._target_index += 1
            self._keep = keep
            if keep:
                self._time = t
                boundary = list(getattr(geometry, "boundary", []) or [])
                self._front = np.array(boundary, dtype=float).reshape(-1, 2) if boundary else np.empty((0, 2))
                self._buffer = []

        def on_element(self, node: Any) -> None:
            if not self._keep or node.is_outside:
                return
            self._buffer.append((
                float(node.x),
                float(node.y),
                int(node.grid_i),
                int(node.grid_j),
                [float(node.concentration(i)) for i in range(len(species))],
            ))

        def on_iteration_complete(self) -> None:
            if not self._keep:
                return
            self._keep = False
            x = np.array([row[0] for row in self._buffer], dtype=float)
            y = np.array([row[1] for row in self._buffer], dtype=float)
            grid_i = np.array([row[2] for row in self._buffer], dtype=int)
            grid_j = np.array([row[3] for row in self._buffer], dtype=int)
            concentrations = {
                name: np.array([row[4][i] for row in self._buffer], dtype=float) for i, name in enumerate(species)
            }
            result.frames.append(
                MovingBoundaryFrame(
                    time=self._time,
                    front=self._front,
                    x=x,
                    y=y,
                    grid_i=grid_i,
                    grid_j=grid_j,
                    concentrations=concentrations,
                )
            )

        def on_complete(self) -> None:
            pass

    solver = mb.MovingBoundarySolver.from_xml(str(setup_xml_file))
    solver.add_element_observer(_Collector(), name="pyvcell_collector")
    solver.run()
    return result
