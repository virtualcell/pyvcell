from pathlib import Path
from typing import Optional, Union

import numpy as np
import zarr

from pyvcell.data_model.plotter import Plotter
from pyvcell.data_model.var_types import NDArray2D
from pyvcell.data_model.vtk_data import VtkData
from pyvcell.data_model.zarr_types import Channel
from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.postprocessing import PostProcessing
from pyvcell.simdata.simdata_models import DataFunctions, PdeDataSet
from pyvcell.simdata.zarr_writer import write_zarr
from pyvcell.utils import slice_dataset


class Result:
    sim_dir: int
    job_id: int
    zarr_dir: Path
    solver_output_dir: Path
    mesh: CartesianMesh
    pde_dataset: PdeDataSet
    data_functions: DataFunctions

    def __init__(
        self,
        solver_output_dir: Path,
        sim_id: int,
        job_id: int,
        zarr_dir: Optional[Path] = None,
        out_dir: Optional[Path] = None,
    ) -> None:
        self.solver_output_dir = solver_output_dir
        self.out_dir = out_dir or solver_output_dir
        if zarr_dir is not None:
            self.zarr_dir = zarr_dir
        else:
            self.zarr_dir = self.solver_output_dir / "zarr"
        self.sim_id = sim_id
        self.job_id = job_id
        self.pde_dataset = PdeDataSet(
            base_dir=self.solver_output_dir, log_filename=f"SimID_{self.sim_id}_{self.job_id}_.log"
        )
        self.pde_dataset.read()
        self.data_functions = DataFunctions(
            function_file=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.functions"
        )
        self.data_functions.read()
        self.mesh = CartesianMesh(mesh_file=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.mesh")
        self.mesh.read()
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
    def concentrations(self) -> NDArray2D:
        data: list[list[float]] = [c.mean_values for c in self.channels if c.index > 0 and c.mean_values is not None]
        return np.array(dtype=np.float64, object=data)

    @property
    def channels(self) -> list[Channel]:
        return [
            Channel(**channel)
            for channel in self.zarr_dataset.attrs.asdict()["metadata"]["channels"]
            if channel["index"] > 4
        ]

    @property
    def num_timepoints(self) -> int:
        shape: tuple[int] = self.zarr_dataset.shape
        return shape[0]  # Assuming time is first dimension

    @property
    def volume_variable_names(self) -> list[str]:
        var_names = []
        for var in self.pde_dataset.variables_block_headers():
            var_name = var.var_info.var_name
            print(var_name, var.var_info.variable_type)
            if "::" in var_name:
                var_names.append(var_name)
        return var_names

    @property
    def plotter(self) -> Plotter:
        return Plotter(
            times=self.get_times(),
            concentrations=self.concentrations,
            channels=self.channels,
            post_processing=self.post_processing,
            zarr_dataset=self.zarr_dataset,
            mesh=self.mesh,
        )

    @property
    def vtk_data(self) -> VtkData:
        return VtkData(
            mesh=self.mesh,
            times=self.get_times(),
            volume_variable_names=self.volume_variable_names,
            pde_dataset=self.pde_dataset,
            out_dir=self.out_dir,
        )

    def get_channel_ids(self) -> list[str]:
        ids = []
        for _i, channel in enumerate(self.channels):
            name = channel.domain_name
            ids.append(name)
        return ids

    def get_times(self) -> list[float]:
        times: list[float] = self.zarr_dataset.attrs.asdict()["metadata"]["times"]
        return times

    def get_time_axis(self, time_index: Optional[int] = None) -> float | list[float]:
        """
        Get x-axis data of times specified by `time_index`.
        """
        times: list[float] = self.get_times()
        return times[time_index] if time_index is not None else times

    def slice_dataset(self, time_index: int, channel_index: int, z_index: int) -> NDArray2D:
        return slice_dataset(
            zarr_dataset=self.zarr_dataset, time_index=time_index, channel_index=channel_index, z_index=z_index
        )


#     def plot_concentrations(self) -> None:
#         t = self.get_time_axis()
#
#         fig, ax = plt.subplots()
#         ax.plot(t, self.concentrations.T)
#         ax.set(xlabel="time (s)", ylabel="concentration", title="Concentration over time")
#
#         y_labels = [c.label for c in self.channels if c.index > 0]
#         ax.legend(y_labels)
#         ax.grid()
#
#     def plot_slice_2d(self, time_index: int, channel_index: int, z_index: int) -> None:
#         data_slice = self.slice_dataset(time_index, channel_index, z_index)
#
#         t = self.zarr_dataset.attrs.asdict()["metadata"]["times"][time_index]
#         channel_label = self.channels[channel_index].label
#         channel_domain = self.channels[channel_index].domain_name
#         z_coord = self.mesh.origin[2] + z_index * self.mesh.extent[2] / (self.mesh.size[2] - 1)
#         title = f"{channel_label} (in {channel_domain}) at t={t}, slice z={z_coord}"
#
#         # Display the slice as an image
#         plt.imshow(data_slice)
#         plt.title(title)
#         return plt.show()
#
#     def plot_slice_3d(self, time_index: int, channel_index: int) -> None:
#         # Select a 3D volume for a single time point and channel, shape is (z, y, x)
#         volume = self.zarr_dataset[time_index, channel_index, :, :, :]
#
#         # Create a figure for 3D plotting
#         fig = plt.figure()
#         ax = fig.add_subplot(111, projection="3d")
#
#         # Define a mask to display the volume (use 'region_mask' channel)
#         mask = np.copy(self.zarr_dataset[3, 0, :, :, :])
#         z, y, x = np.where(mask == 1)
#
#         # Get the intensity values for these points
#         intensities = volume[z, y, x]
#
#         # Create a 3D scatter plot
#         scatter = ax.scatter(x, y, z, c=intensities, cmap="viridis")
#
#         # Add a color bar to represent intensities
#         fig.colorbar(scatter, ax=ax, label="Intensity")
#
#         # Set labels for axes
#         ax.set_xlabel("X")
#         ax.set_ylabel("Y")
#         ax.set_zlabel("Z")  # type: ignore[attr-defined]
#
#         # Show the plot
#         return plt.show()
#
#     def plot_image(self, image_index: int, time_index: int) -> None:
#         # display image dataset "fluor" at time index 4 as an image
#         img_metadata = self.post_processing.image_metadata[image_index]
#         image_data: np.typing.NDArray[np.float64] = self.post_processing.read_image_data(
#             image_metadata=img_metadata, time_index=time_index
#         )
#         plt.imshow(image_data)
#         plt.title(f"post processing image data '{img_metadata.name}' at time index {time_index}")
#         return plt.show()
#
#     def _get_mesh(self) -> CartesianMesh:
#         mesh = CartesianMesh(mesh_file=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.mesh")
#         mesh.read()
#         return mesh
#
#     def get_3d_slice_animation(self, channel_index: int, interval: int = 200) -> animation.FuncAnimation:
#         """
#         Animate the 3D scatter plot over time.
#
#         Parameters:
#             channel_index (int): The index of the channel to visualize.
#             interval (int): Time interval between frames in milliseconds.
#         """
#         # Extract metadata and the number of time points
#         channel_list = self.channels
#         channel_domain = channel_list[channel_index - 5].domain_name
#         num_timepoints = self.num_timepoints
#
#         # Create a figure for 3D plotting
#         fig = plt.figure()
#         ax = fig.add_subplot(111, projection="3d")
#
#         # Set labels for axes
#         ax.set_xlabel("X")
#         ax.set_ylabel("Y")
#         ax.set_zlabel("Z")  # type: ignore[attr-defined]
#         sc = None
#
#         @no_type_check
#         def update(frame: int):
#             """Update function for animation"""
#             # Define a mask to display the volume (use 'region_mask' channel)
#             mask = np.copy(self.zarr_dataset[frame, 0, :, :, :])
#             z, y, x = np.where(mask == 1)
#
#             volume = self.zarr_dataset[frame, channel_index, :, :, :]
#             intensities = volume[z, y, x]
#
#             # Initialize the scatter plot with empty data
#             scatter = ax.scatter(x, y, z, c=intensities, cmap="viridis")
#             ax.set_title(f"Channel: {channel_domain}, Time Index: {frame}")
#             return (scatter,)
#
#         # Create the animation
#         fig.colorbar(sc, ax=ax, label="Intensity")  # type: ignore[arg-type]
#         ani = animation.FuncAnimation(fig, update, num_timepoints, interval=interval, blit=False)
#
#         return ani
#
#     @no_type_check
#     def render_animation(self, ani: animation.FuncAnimation) -> HTML:
#         return HTML(ani.to_jshtml())
#
#     def animate_channel_3d(self, channel_index: int) -> Any:
#         ani = self.get_3d_slice_animation(channel_index)
#         return self.render_animation(ani)
#
#     def get_image_animation(self, image_index: int, interval: int = 200) -> animation.FuncAnimation:
#         """
#         Animate the fluorescence image over time.
#
#         Parameters:
#             image_index (int): The index of the image to visualize.
#             interval (int): Time interval between frames in milliseconds.
#         """
#         post_processing = self.post_processing
#
#         # Create figure and axis for animation
#         fig = plt.figure()
#         ax = fig.add_subplot()
#
#         # Set title
#         title = ax.set_title("Post-processing image data 'fluor' at time index 0")
#
#         @no_type_check
#         def update(frame: int):
#             """Update function for animation"""
#             img_metadata = post_processing.image_metadata[image_index]
#             image_data = post_processing.read_image_data(image_metadata=img_metadata, time_index=frame)
#             img_plot = ax.imshow(image_data)
#             # img_plot.set_data(image_data)  # Update image
#             title.set_text(f"Post-processing image data 'fluor' at time index {frame}")
#             plt.show()
#             return (img_plot,)
#
#         # Create the animation
#         ani = animation.FuncAnimation(fig, update, frames=self.num_timepoints, interval=interval, blit=False)
#
#         return ani
#
#     @no_type_check
#     def animate_image(self, image_index: int) -> HTML:
#         ani = self.get_image_animation(image_index)
#         return self.render_animation(ani)
