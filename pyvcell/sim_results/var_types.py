from typing import TypeAlias

import numpy as np

NDArray1D: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]
NDArray2D: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
NDArray3D: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[np.float64]]
NDArray4D: TypeAlias = np.ndarray[tuple[int, int, int, int], np.dtype[np.float64]]
NDArrayND: TypeAlias = np.ndarray[tuple[int, ...], np.dtype[np.float64]]

NDArray1Du8: TypeAlias = np.ndarray[tuple[int], np.dtype[np.uint8]]
NDArray2Du8: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.uint8]]
NDArray3Du8: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[np.uint8]]

NDArray1Du32: TypeAlias = np.ndarray[tuple[int], np.dtype[np.uint32]]
