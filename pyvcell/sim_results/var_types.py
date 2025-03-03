from typing import TypeAlias

import numpy as np

NDArray1D: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]
NDArray2D: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
NDArray3D: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[np.float64]]
