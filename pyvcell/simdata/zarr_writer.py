from pathlib import Path
from typing import Any

import numpy as np
import zarr
from numpy._typing import NDArray

from pyvcell.data_model.var_types import NDArray1D, NDArray3D
from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.simdata_models import DataBlockHeader, DataFunctions, NamedFunction, PdeDataSet, VariableType


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

        # add volumetric state variables
        for i, v in enumerate(volume_data_vars):
            var_data: NDArray[np.float64] = pde_dataset.get_data(v.var_info, times[t]).reshape((num_z, num_y, num_x))
            c = i + 5
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
            channel_metadata[c]["min_values"].append(np.min(var_data))
            channel_metadata[c]["max_values"].append(np.max(var_data))
            channel_metadata[c]["mean_values"].append(np.mean(var_data))

        # add volumetric functions
        for j, f in enumerate(volume_functions):
            func_data = f.evaluate(variable_bindings=bindings).reshape((num_z, num_y, num_x))
            c = i + j + 6
            z1[t, c, :, :, :] = func_data
            domain_name = f.name.split("::")[0]
            function_name = f.name.split("::")[1]
            if t == 0:
                channel_metadata.append({
                    "index": (i + j + 5),
                    "label": function_name,
                    "domain_name": domain_name,
                    "min_values": [],
                    "max_values": [],
                    "mean_values": [],
                })
            channel_metadata[c]["min_values"].append(np.min(func_data))
            channel_metadata[c]["max_values"].append(np.max(func_data))
            channel_metadata[c]["mean_values"].append(np.mean(func_data))

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
