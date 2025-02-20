from typing import Union

import numpy as np
import zarr

from pyvcell.data_model.var_types import NDArray2D


def slice_dataset(
    zarr_dataset: Union[zarr.Group, zarr.Array], time_index: int, channel_index: int, z_index: int
) -> NDArray2D:
    ds = zarr_dataset
    data: list[list[float]] = ds[time_index, channel_index, z_index, :, :].tolist()
    return np.array(data)
