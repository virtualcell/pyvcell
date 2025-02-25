from pathlib import Path
from typing import Union

import numpy as np
import toml
import zarr

from pyvcell.data_model.var_types import NDArray2D


class ProjectVersion:
    current: str
    major: int
    minor: int
    patch: int

    def __init__(self, pyproject_file: Union[str, Path]):
        self.current = toml.load(pyproject_file)["tool"]["poetry"]["version"]
        self.major, self.minor, self.patch = tuple([int(item) for item in self.current.split(".")])

    def __repr__(self) -> str:
        return self.current


def get_project_version(pyproject_path: Union[str, Path]) -> ProjectVersion:
    return ProjectVersion(pyproject_path)


def slice_dataset(
    zarr_dataset: Union[zarr.Group, zarr.Array], time_index: int, channel_index: int, z_index: int
) -> NDArray2D:
    ds = zarr_dataset
    data: list[list[float]] = ds[time_index, channel_index, z_index, :, :].tolist()
    return np.array(data)
