import shutil
from pathlib import Path
from typing import Optional, Union

import numpy as np
import zarr

from pyvcell._internal.simdata.mesh import CartesianMesh
from pyvcell._internal.simdata.postprocessing import PostProcessing
from pyvcell._internal.simdata.simdata_models import DataFunctions, PdeDataSet
from pyvcell._internal.simdata.zarr_writer import write_zarr
from pyvcell.sim_results.plotter import Plotter
from pyvcell.sim_results.var_types import NP2DArray, NP3DArray
from pyvcell.sim_results.vtk_data import VtkData
from pyvcell.sim_results.zarr_types import (
    AxisMetadata,
    # Channel,
    ChannelMetadata,
    MeshMetadata,
    MeshVolumeRegion,
    ZarrMetadata,
)
from pyvcell.sim_results.zarr_utils import slice_dataset_3d


class Result:
    """
    Creates (or copies) the results of a PDE simulation
    Required Parameters:
        solver_output_dir: Path
        sim_id: int
        job_id: int
    Optional Parameters:
        zarr_dir: Path
        out_dir: Path
    Parameters only used for copying
        pde_dataset: PdeDataSet
        data_functions: DataFunctions
        mesh: CartesianMesh
    """
    def __init__(
        self,
        solver_output_dir: Path,
        sim_id: int,
        job_id: int,
        zarr_dir: Optional[Path] = None,
        out_dir: Optional[Path] = None,
        pde_dataset: PdeDataSet | None = None,
        data_functions: DataFunctions | None = None,
        mesh: CartesianMesh | None = None,

    ) -> None:
        self.solver_output_dir: Path = solver_output_dir
        self.sim_id: int = sim_id
        self.job_id: int = job_id
        self.zarr_dir: Path = zarr_dir if zarr_dir is not None else self.solver_output_dir / "zarr"
        self.out_dir: Path = out_dir or solver_output_dir

        # Generate PDE DataSet
        self.pde_dataset: PdeDataSet
        if pde_dataset is not None:
            self.pde_dataset = pde_dataset
            # sanity checks:
            if self.pde_dataset.base_dir != self.solver_output_dir:
                raise ValueError("PDE Dataset and solver output dir are not correlated.")
            if self.sim_id not in self.pde_dataset.log_filename or self.job_id not in self.pde_dataset.log_filename:
                raise ValueError("Log file identifiers do not match expected sim and/or job id.")
        else:
            self.pde_dataset: PdeDataSet = PdeDataSet(
                base_dir=self.solver_output_dir, log_filename=f"SimID_{self.sim_id}_{self.job_id}_.log"
            )
            self.pde_dataset.read()

        # Generate Data Functions
        self.data_functions: DataFunctions
        if data_functions is not None:
            self.data_functions = data_functions
            # sanity checks:
            if self.data_functions.function_file.parent != self.solver_output_dir:
                raise ValueError("Directory containing data functions file does not match solver output directory.")
            filename: str = self.data_functions.function_file.name
            if self.sim_id not in filename or self.job_id not in filename:
                raise ValueError("Data functions file identifiers do not match expected sim and/or job id.")
        else:
            self.data_functions: DataFunctions = DataFunctions(
                function_file=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.functions"
            )
            self.data_functions.read()

        # Generate Cartesian Mesh
        self.mesh: CartesianMesh
        if mesh is not None:
            self.mesh = mesh
            # sanity checks:
            if self.mesh.mesh_file.parent != self.solver_output_dir:
                raise ValueError("Directory containing mesh file does not match solver output directory.")
            filename: str = self.mesh.mesh_file.name
            if self.sim_id not in filename or self.job_id not in filename:
                raise ValueError("Mesh file identifiers do not match expected sim and/or job id.")
        else:
            self.mesh: CartesianMesh = CartesianMesh(
                mesh_file=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.mesh")
            self.mesh.read()


        # Write data to Zarr Directory (if not a pure copy)
        if pde_dataset is None or data_functions is None or mesh is None:
            write_zarr(
                pde_dataset=self.pde_dataset, data_functions=self.data_functions, mesh=self.mesh, zarr_dir=self.zarr_dir
            )

    @property
    def zarr_dataset(self) -> Union[zarr.Group, zarr.Array]:
        return zarr.open(str(self.zarr_dir), mode="r")

    @property
    def post_processing(self) -> PostProcessing:
        post_processing = PostProcessing(
            postprocessing_hdf5_path=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.hdf5"
        )
        post_processing.read()
        return post_processing

    @property
    def concentrations(self) -> NP2DArray:
        data: list[list[float] | None]  = [
            c.mean_values for c in self.channel_data if c.index > 0 and c.mean_values is not None
        ]
        return np.array(dtype=np.float64, object=data)

    @property
    def channel_data(self) -> list[ChannelMetadata]:
        return [ChannelMetadata(**channel) for channel in self.zarr_dataset.attrs.asdict()["metadata"]["channels"]]

    @property
    def num_timepoints(self) -> int:
        shape: tuple[int] = self.zarr_dataset.shape
        return shape[0]  # Assuming time is first dimension

    @property
    def volume_variable_names(self) -> list[str]:
        var_names = []
        for var in self.pde_dataset.variables_block_headers():
            var_name = var.var_info.var_name
            # print(var_name, var.var_info.variable_type)
            if "::" in var_name:
                var_names.append(var_name)
        return var_names

    @property
    def metadata(self) -> ZarrMetadata:
        md = self.zarr_dataset.attrs.asdict()["metadata"]
        axes = [AxisMetadata(**ax) for ax in md.get("axes")]
        # channels = [ChannelMetadata(**channel) for channel in md.get("channels") if channel["index"] > 4]
        times = md.get("times")

        mesh_meta = md.get("mesh")
        regions = [MeshVolumeRegion(**region) for region in mesh_meta.get("volume_regions")]
        mesh = MeshMetadata(
            size=mesh_meta.get("size"),
            extent=mesh_meta.get("extent"),
            origin=mesh_meta.get("origin"),
            volume_regions=regions,
        )

        return ZarrMetadata(axes=axes, channels=self.channel_data, times=times, mesh=mesh)

    @property
    def plotter(self) -> Plotter:
        return Plotter(
            times=self.time_points,
            concentrations=self.concentrations,
            channels=self.channel_data,
            post_processing=self.post_processing,
            zarr_dataset=self.zarr_dataset,
            mesh=self.mesh,
            metadata=self.metadata,
        )

    @property
    def vtk_data(self) -> VtkData:
        return VtkData(
            mesh=self.mesh,
            times=self.time_points,
            volume_variable_names=self.volume_variable_names,
            pde_dataset=self.pde_dataset,
            out_dir=self.out_dir,
        )

    def get_channel_ids(self) -> list[str]:
        # ids = []
        # for _i, channel in enumerate(self.channels):
        #     name = channel.domain_name
        #     ids.append(name)
        # return ids
        return [channel.label for channel in self.channel_data]

    def get_channel(self, label: str) -> ChannelMetadata:
        getter = filter(lambda c: c.label == label, self.channel_data)
        channel_data = next(getter, None)

        if channel_data is None:
            raise ValueError(f"No channel found with label '{label}'")
        if next(getter, None) is not None:
            raise ValueError(f"More than one '{label}' channel found")
        if not isinstance(channel_data, ChannelMetadata):
            raise ValueError(f"Channel label '{label}' refers to something that is not a channel label")
        return channel_data

    def get_slice(
        self,
        channel_id: str,
        time_index: int,
    ) -> NP3DArray:
        channel = self.get_channel(channel_id)
        return slice_dataset_3d(channel, self.zarr_dataset, time_index)

    @property
    def time_points(self) -> list[float]:
        times: list[float] = self.zarr_dataset.attrs.asdict()["metadata"]["times"]
        return times

    @property
    def time_indices(self) -> list[int]:
        return [i for i, v in enumerate(self.time_points)]

    def get_time_axis(self, time_index: Optional[int] = None) -> float | list[float]:
        """
        Get x-axis data of times specified by `time_index`.
        """
        times: list[float] = self.time_points
        return times[time_index] if time_index is not None else times

    def cleanup(self) -> None:
        shutil.rmtree(self.out_dir)
