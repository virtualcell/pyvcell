import zarr

from pyvcell.sim_results.var_types import NP2DArray, NP3DArray
from pyvcell.sim_results.zarr_types import ChannelMetadata


def slice_dataset_2d(
    channel: ChannelMetadata,
    dataset: zarr.Group | zarr.Array,
    time_index: int,
    z_index: int,
) -> NP2DArray:
    slice2d: NP2DArray = dataset[time_index, channel.index, z_index, :, :]
    return slice2d


def slice_dataset_3d(channel: ChannelMetadata, dataset: zarr.Group | zarr.Array, time_index: int) -> NP3DArray:
    slice3d: NP3DArray = dataset[time_index, channel.index, :, :, :]
    return slice3d
