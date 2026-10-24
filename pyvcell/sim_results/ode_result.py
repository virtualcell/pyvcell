"""Result of a non-spatial (ODE) simulation.

VCell's Sundials ODE solvers write one table: a column per state variable (and ``t``), a row per saved time
point (the ``.ida`` file). These objects hold only numpy arrays and plain Python, so they can be inspected and
post-processed without any heavy optional dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class OdeResult:
    """The time course of a non-spatial simulation.

    Attributes:
        times: ``(T,)`` the saved time points, increasing.
        variable_names: the solved variables, in column order (the time column excluded).
        values: ``(T, V)`` each variable's value at each time point.
    """

    times: np.ndarray
    variable_names: list[str]
    values: np.ndarray

    def __getitem__(self, name: str) -> np.ndarray:
        """One variable's time course, by name."""
        try:
            return np.asarray(self.values[:, self.variable_names.index(name)])
        except ValueError:
            raise KeyError(f"no variable {name!r}; there are {self.variable_names}") from None

    def as_dict(self) -> dict[str, np.ndarray]:
        """``{"t": times, name: values, ...}``, e.g. for ``pandas.DataFrame(result.as_dict())``."""
        return {"t": self.times, **{name: self[name] for name in self.variable_names}}

    @classmethod
    def from_ida_file(cls, path: Path | str) -> OdeResult:
        """Read the ``.ida`` file VCell's ODE solvers write: a header of colon-separated column names (``t`` first),
        then one tab-separated row per time point. Reading stops at an incomplete row, as VCell's own reader does
        (a run cut off while writing)."""
        lines = Path(path).read_text().splitlines()
        if not lines:
            raise ValueError(f"{path}: empty ODE results file")
        names = [name for name in lines[0].split(":") if name]
        if not names or names[0] != "t":
            raise ValueError(f"{path}: expected a header starting with 't:', got {lines[0][:80]!r}")
        rows: list[list[float]] = []
        for line in lines[1:]:
            fields = line.split()
            if len(fields) < len(names):
                break
            rows.append([float(v) for v in fields[: len(names)]])
        table = np.array(rows, dtype=float).reshape(len(rows), len(names))
        return cls(times=table[:, 0], variable_names=names[1:], values=table[:, 1:])
