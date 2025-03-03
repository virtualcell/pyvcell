import zarr

from pyvcell.sim_results.var_types import NDArray2D, NDArray3D
from pyvcell.sim_results.zarr_types import ChannelMetadata


def slice_dataset_2d(
    channel: ChannelMetadata,
    dataset: zarr.Group | zarr.Array,
    time_index: int,
    z_index: int,
) -> NDArray2D:
    slice2d: NDArray2D = dataset[time_index, channel.index, z_index, :, :]
    return slice2d


def slice_dataset_3d(channel: ChannelMetadata, dataset: zarr.Group | zarr.Array, time_index: int) -> NDArray3D:
    slice3d: NDArray3D = dataset[time_index, channel.index, :, :, :]
    return slice3d
