from typing import Optional

import numpy as np
import zarr

from pyvcell.data_model.var_types import NDArray2D, NDArray3D
from pyvcell.data_model.zarr_types import ChannelMetadata
from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.simdata_models import PdeDataSet

# def slice_dataset(
#     zarr_dataset: Union[zarr.Group, zarr.Array], time_index: int, channel_index: int, z_index: int
# ) -> NDArray2D:
#     ds = zarr_dataset
#     data: list[list[float]] = ds[time_index, channel_index, z_index, :, :].tolist()
#     return np.array(data)


def get_mask(pde_dataset: PdeDataSet, mesh: CartesianMesh) -> NDArray3D:
    header = pde_dataset.first_data_zip_file_metadata().file_header
    num_x: int = header.sizeX
    num_y: int = header.sizeY
    num_z: int = header.sizeZ
    return mesh.volume_region_map.reshape((num_z, num_y, num_x)).astype(np.float64)


def slice_dataset(
    channel: ChannelMetadata,
    dataset: zarr.Group | zarr.Array,
    time_index: int,
    z_index: Optional[int] = None,
) -> NDArray2D | NDArray3D:
    return (
        slice_dataset_2d(channel, dataset, time_index, z_index)
        if z_index is not None
        else slice_dataset_3d(channel, dataset, time_index)
    )


def slice_dataset_2d(
    channel: ChannelMetadata,
    dataset: zarr.Group | zarr.Array,
    time_index: int,
    z_index: Optional[int] = None,
) -> NDArray2D:
    slice2d: NDArray2D = dataset[time_index, channel.index, z_index, :, :]
    return slice2d


def slice_dataset_3d(channel: ChannelMetadata, dataset: zarr.Group | zarr.Array, time_index: int) -> NDArray3D:
    slice3d: NDArray3D = dataset[time_index, channel.index, :, :, :]
    return slice3d
