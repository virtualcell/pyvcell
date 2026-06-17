
from typing import TypeAlias, Literal

import numpy as np

from nptyping import NDArray, Float64, UInt8, UInt32, Int32 # no idea why `Shape` causes errors!

# Old typing methodology
NDArray1D: TypeAlias = np.ndarray[tuple[int], np.dtype[np.float64]]
NDArray2D: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.float64]]
NDArray3D: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[np.float64]]
NDArray4D: TypeAlias = np.ndarray[tuple[int, int, int, int], np.dtype[np.float64]]
NDArrayND: TypeAlias = np.ndarray[tuple[int, ...], np.dtype[np.float64]]

NDArray1Du8: TypeAlias = np.ndarray[tuple[int], np.dtype[np.uint8]]
NDArray2Du8: TypeAlias = np.ndarray[tuple[int, int], np.dtype[np.uint8]]
NDArray3Du8: TypeAlias = np.ndarray[tuple[int, int, int], np.dtype[np.uint8]]

NDArray1Du32: TypeAlias = np.ndarray[tuple[int], np.dtype[np.uint32]]

# nptyping methodology
# no idea why `Shape` causes errors! But "Literal" works, so consider them synonyms!
NP1DArray: TypeAlias = NDArray[Literal["*"], Float64]
NP1DArray_u8: TypeAlias = NDArray[Literal["*"], UInt8]
NP1DArray_u32: TypeAlias = NDArray[Literal["*"], UInt32]

NP2DArray: TypeAlias = NDArray[Literal["*,*"], Float64]
NP2DArray_nx8_i32: TypeAlias = NDArray[Literal['*, 8'], Int32]

NP3DArray: TypeAlias = NDArray[Literal["*,*,*"], Float64]

NP4DArray: TypeAlias = NDArray[Literal['*,*,*,*'], Float64]
NP4DArray_lxwxhx3: TypeAlias = NDArray[Literal['*,*,*,3'], Float64]
