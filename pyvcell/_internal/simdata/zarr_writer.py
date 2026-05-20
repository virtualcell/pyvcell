from pathlib import Path
from typing import Any

import numpy as np
import zarr
from numpy._typing import NDArray

from pyvcell._internal.simdata.mesh import CartesianMesh
from pyvcell._internal.simdata.simdata_models import (
    DataBlockHeader,
    DataFunctions,
    NamedFunction,
    PdeDataSet,
    VariableType,
)
from pyvcell.sim_results.var_types import NDArray1D, NDArray3D


def write_zarr(pde_dataset: PdeDataSet, data_functions: DataFunctions, mesh: CartesianMesh, zarr_dir: Path) -> None:
    volume_data_vars: list[DataBlockHeader] = [
        v for v in pde_dataset.variables_block_headers() if v.var_info.variable_type == VariableType.VOLUME
    ]
    volume_functions: list[NamedFunction] = [
        f for f in data_functions.named_functions if f.variable_type == VariableType.VOLUME
    ]
    num_channels = len(volume_data_vars) + len(volume_functions) + 5  # 5 extra channels for region map, t, x, y, z
    num_t: int = len(pde_dataset.times())
    times: list[float] = pde_dataset.times()
    header = pde_dataset.first_data_zip_file_metadata().file_header
    num_x: int = header.sizeX
    num_y: int = header.sizeY
    num_z: int = header.sizeZ

    z1 = zarr.open(
        str(zarr_dir.absolute()),
        mode="w",
        shape=(num_t, num_channels, num_z, num_y, num_x),
        chunks=(1, 1, num_z, num_y, num_x),
        dtype=float,
    )

    # add spatial coordinates
    region_map: NDArray3D = mesh.volume_region_map.reshape((num_z, num_y, num_x)).astype(np.float64)
    x: NDArray1D = np.linspace(mesh.origin[0], mesh.origin[0] + mesh.extent[0], num_x, dtype=np.float64)
    y: NDArray1D = np.linspace(mesh.origin[1], mesh.origin[1] + mesh.extent[1], num_y, dtype=np.float64)
    z: NDArray1D = np.linspace(mesh.origin[2], mesh.origin[2] + mesh.extent[2], num_z, dtype=np.float64)
    zeros: NDArray3D = np.zeros((num_z, num_y, num_x), dtype=np.float64)
    x_map: NDArray3D = zeros + x[np.newaxis, np.newaxis, :]
    y_map: NDArray3D = zeros + y[np.newaxis, :, np.newaxis]
    z_map: NDArray3D = zeros + z[:, np.newaxis, np.newaxis]

    # Pre-compute domain masks: domain_name -> boolean array over (num_z, num_y, num_x)
    region_map_flat = mesh.volume_region_map
    _domain_masks: dict[str, np.ndarray] = {}

    def _get_domain_mask(dname: str) -> np.ndarray:
        if dname not in _domain_masks:
            vol_reg_ids = mesh.get_volume_region_ids(volume_domain_name=dname)
            mask_flat = np.isin(region_map_flat, list(vol_reg_ids))
            _domain_masks[dname] = mask_flat.reshape((num_z, num_y, num_x))
        return _domain_masks[dname]

    channel_metadata: list[dict[str, Any]] = []
    for t in range(num_t):
        bindings = {}

        z1[t, 0, :, :, :] = region_map
        bindings["region_mask"] = region_map

        times_map: NDArray3D = zeros + np.array(times[t])[np.newaxis, np.newaxis, np.newaxis]
        z1[t, 1, :, :, :] = times_map
        bindings["t"] = times_map

        z1[t, 2, :, :, :] = x_map
        bindings["x"] = x_map

        z1[t, 3, :, :, :] = y_map
        bindings["y"] = y_map

        z1[t, 4, :, :, :] = z_map
        bindings["z"] = z_map

        if t == 0:
            channel_metadata.append({
                "index": 0,
                "label": "region_mask",
                "domain_name": "all",
                "min_value": np.min(region_map),
                "max_value": np.max(region_map),
            })
            channel_metadata.append({
                "index": 1,
                "label": "t",
                "domain_name": "all",
                "min_value": times[0],
                "max_value": times[-1],
            })
            channel_metadata.append({
                "index": 2,
                "label": "x",
                "domain_name": "all",
                "min_value": mesh.origin[0],
                "max_value": mesh.origin[0] + mesh.extent[0],
            })

            channel_metadata.append({
                "index": 3,
                "label": "y",
                "domain_name": "all",
                "min_value": mesh.origin[1],
                "max_value": mesh.origin[1] + mesh.extent[1],
            })
            channel_metadata.append({
                "index": 4,
                "label": "z",
                "domain_name": "all",
                "min_value": mesh.origin[2],
                "max_value": mesh.origin[2] + mesh.extent[2],
            })

        c = 5
        # add volumetric state variables
        for v in volume_data_vars:
            var_data: NDArray[np.float64] = pde_dataset.get_data(v.var_info, times[t]).reshape((num_z, num_y, num_x))
            z1[t, c, :, :, :] = var_data
            domain_name = v.var_info.var_name.split("::")[0]
            var_name = v.var_info.var_name.split("::")[1]
            bindings[var_name] = var_data
            if t == 0:
                channel_metadata.append({
                    "index": c,
                    "label": var_name,
                    "domain_name": domain_name,
                    "min_values": [],
                    "max_values": [],
                    "mean_values": [],
                })
            domain_mask = _get_domain_mask(domain_name)
            masked = var_data[domain_mask]
            channel_metadata[c]["min_values"].append(float(np.min(masked)))
            channel_metadata[c]["max_values"].append(float(np.max(masked)))
            channel_metadata[c]["mean_values"].append(float(np.mean(masked)))
            c = c + 1

        # add volumetric functions
        for f in volume_functions:
            evaluated_data = f.evaluate(variable_bindings=bindings)
            is_pre_sized: bool = evaluated_data.shape == (num_z, num_y, num_x)
            if evaluated_data.shape == ():  # scalar value
                func_data = np.zeros((num_z, num_y, num_x), dtype=evaluated_data.dtype)
                func_data.fill(evaluated_data.min())  # min of a scalar value is the value itself.
            else:
                func_data = evaluated_data if is_pre_sized else evaluated_data.reshape((num_z, num_y, num_x))
            z1[t, c, :, :, :] = func_data
            name_parts = f.name.split("::")
            if len(name_parts) > 2:
                raise ValueError(f"Volume function name `{f.name}` is not in the expected format")
            domain_half: str = f.name.split("::")[0] if len(name_parts) == 2 else ""
            name_half: str = f.name.split("::")[-1]
            if t == 0:
                channel_metadata.append({
                    "index": c,
                    "label": name_half,
                    "domain_name": domain_half,
                    "min_values": [],
                    "max_values": [],
                    "mean_values": [],
                })
            masked = func_data if len(domain_half) == 0 else func_data[_get_domain_mask(domain_half)]
            channel_metadata[c]["min_values"].append(float(np.min(masked)))
            channel_metadata[c]["max_values"].append(float(np.max(masked)))
            channel_metadata[c]["mean_values"].append(float(np.mean(masked)))
            c = c + 1

    z1.attrs["metadata"] = {
        "axes": [
            {"name": "t", "type": "time", "unit": "second"},
            {"name": "c", "type": "channel", "unit": None},
            {"name": "z", "type": "space", "unit": "micrometer"},
            {"name": "y", "type": "space", "unit": "micrometer"},
            {"name": "x", "type": "space", "unit": "micrometer"},
        ],
        "channels": channel_metadata,
        "times": times,
        "mesh": {
            "size": mesh.size,
            "extent": mesh.extent,
            "origin": mesh.origin,
            "volume_regions": [
                {
                    "region_index": mesh.volume_regions[i][0],
                    "domain_type_index": mesh.volume_regions[i][1],
                    "volume": mesh.volume_regions[i][2],
                    "domain_name": mesh.volume_regions[i][3],
                }
                for i in range(len(mesh.volume_regions))
            ],
        },
    }
    z1.attrs["metadata"]["mesh"] = {
        "size": mesh.size,
        "extent": mesh.extent,
        "origin": mesh.origin,
        "volume_regions": [
            {
                "region_index": mesh.volume_regions[i][0],
                "domain_type_index": mesh.volume_regions[i][1],
                "volume": mesh.volume_regions[i][2],
                "domain_name": mesh.volume_regions[i][3],
            }
            for i in range(len(mesh.volume_regions))
        ],
    }
