from typing import Union, no_type_check

import matplotlib.pyplot as plt
import numpy as np
import zarr
from matplotlib import animation
from matplotlib.collections import PathCollection

from pyvcell._internal.simdata.mesh import CartesianMesh
from pyvcell._internal.simdata.postprocessing import PostProcessing, VariableInfo
from pyvcell.sim_results.var_types import NDArray2D
from pyvcell.sim_results.zarr_types import ChannelMetadata, ZarrMetadata
from pyvcell.sim_results.zarr_types import ChannelMetadata as Channel
from pyvcell.sim_results.zarr_utils import slice_dataset_2d

plt.rcParams["animation.html"] = "jshtml"
plt.rcParams["figure.dpi"] = 150
plt.ioff()


class Plotter:
    times: list[float]
    concentrations: NDArray2D
    channels: list[Channel]
    post_processing: PostProcessing
    zarr_dataset: Union[zarr.Group, zarr.Array]
    mesh: CartesianMesh
    metadata: ZarrMetadata

    def __init__(
        self,
        times: list[float],
        concentrations: NDArray2D,
        channels: list[Channel],
        post_processing: PostProcessing,
        zarr_dataset: Union[zarr.Group, zarr.Array],
        mesh: CartesianMesh,
        metadata: ZarrMetadata,
    ) -> None:
        self.times = times
        self.num_timepoints = len(times)
        self.concentrations = concentrations
        self.channels = channels
        self.post_processing = post_processing
        self.zarr_dataset = zarr_dataset
        self.mesh = mesh
        self.metadata = metadata

    def get_channel(self, label: str) -> ChannelMetadata:
        getter = filter(lambda c: c.label == label, self.channels)
        channel_data = next(getter, None)

        if channel_data is None:
            raise ValueError(f"No channel found with label '{label}'")
        if next(getter, None) is not None:
            raise ValueError(f"More than one '{label}' channel found")

        return channel_data

    def plot_concentrations(self) -> None:
        t = self.times
        fig, ax = plt.subplots()
        ax.plot(t, self.concentrations.T)
        ax.set(xlabel="time (s)", ylabel="concentration", title="Concentration over time")

        y_labels = [c.label for c in self.channels if c.mean_values is not None]
        ax.legend(y_labels)
        ax.grid()
        return plt.show()

    def plot_slice_2d(self, time_index: int, channel_name: str, z_index: int) -> None:
        specified_channel = self.get_channel(channel_name)
        data_slice = slice_dataset_2d(specified_channel, self.zarr_dataset, time_index, z_index)

        t = self.zarr_dataset.attrs.asdict()["metadata"]["times"][time_index]
        channel_label = None
        channel_domain = None

        for channel in self.channels:
            if channel.index == specified_channel.index:
                channel_label = channel.label
                channel_domain = channel.domain_name

        # z_coord = self.mesh.origin[2] + z_index * self.mesh.extent[2] / (self.mesh.size[2] - 1)
        title = f"{channel_label} (in {channel_domain}) at t={t}"
        # title = f"{channel_label} (in {channel_domain}) at t={t}, slice z={z_coord}"

        # Display the slice as an image
        plt.imshow(data_slice)
        plt.title(title)
        plt.show()

    def plot_slice_3d(self, time_index: int, channel_id: str) -> None:
        # Select a 3D volume for a single time point and channel, shape is (z, y, x)
        channel = self.get_channel(channel_id)
        volume = self.zarr_dataset[time_index, channel.index, :, :, :]

        # Create a figure for 3D plotting
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")

        # Define a mask to display the volume (use 'region_mask' channel)
        mask = np.copy(self.zarr_dataset[time_index, 0, :, :, :])
        domain = channel.domain_name

        if channel.domain_name == "all":
            z, y, x = np.where(mask > -1)  # everywhere
            # Get the intensity values for these points
            intensities = volume[z, y, x]
        else:
            idx: set[int] = self.mesh.get_volume_region_ids(volume_domain_name=domain)
            region_func = lambda region_index: region_index in idx
            z, y, x = np.where(np.vectorize(region_func)(mask))
            # Get the intensity values for these points
            intensities = volume[z, y, x]

        # Create a 3D scatter plot
        scatter = ax.scatter(x, y, z, c=intensities, cmap="viridis")

        # Add a color bar to represent intensities
        fig.colorbar(scatter, ax=ax, label="Intensity")

        # Set labels for axes
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")  # type: ignore[attr-defined]
        t = self.times[time_index]
        title = f"{channel.label} (in {channel.domain_name}) at t={t}"
        plt.title(title)
        # Show the plot
        return plt.show()

    def plot_image(self, image_index: int, time_index: int) -> None:
        # display image dataset "fluor" at time index 4 as an image
        img_metadata = self.post_processing.image_metadata[image_index]
        image_data: np.typing.NDArray[np.float64] = self.post_processing.read_image_data(
            image_metadata=img_metadata, time_index=time_index
        )
        plt.imshow(image_data)
        plt.title(f"post processing image data '{img_metadata.name}' at time index {time_index}")
        return plt.show()

    def get_3d_slice_animation(self, channel_id: str, interval: int = 200) -> animation.FuncAnimation:
        """
        Animate the 3D scatter plot over time.

        Parameters:
            channel_id (str): The label of the channel to visualize.
            interval (int): Time interval between frames in milliseconds.
        """
        # Extract metadata and the number of time points
        channel = self.get_channel(channel_id)
        num_timepoints = self.num_timepoints

        # Create a figure for 3D plotting
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")

        # Set labels for axes
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")  # type: ignore[attr-defined]
        sc = None

        def update(frame: int) -> tuple[PathCollection]:
            """Update function for animation"""
            mask = np.copy(self.zarr_dataset[3, 0, :, :, :])
            print(f"Any mask: {np.any(mask)}")

            z, y, x = np.where(mask > 0)
            print(f"got shapes: {z.shape}, {y.shape}, {x.shape}")
            volume = self.zarr_dataset[frame, channel.index, :, :, :]
            intensities = volume[z, y, x]

            # Initialize the scatter plot with empty data
            scatter = ax.scatter(x, y, z, c=intensities, cmap="viridis")
            ax.set_title(f"Channel: {channel.domain_name}, Time Index: {frame}")
            return (scatter,)

        # Create the animation
        fig.colorbar(sc, ax=ax, label="Intensity")  # type: ignore[arg-type]
        return animation.FuncAnimation(fig, update, num_timepoints, interval=interval, blit=False)

    def animate_channel_3d(self, channel_id: str) -> animation.FuncAnimation:
        return self.get_3d_slice_animation(channel_id=channel_id)

    def get_image_animation(self, image_index: int, interval: int = 200) -> animation.FuncAnimation:
        """
        Animate the fluorescence image over time.

        Parameters:
            image_index (int): The index of the image to visualize.
            interval (int): Time interval between frames in milliseconds.
        """
        post_processing = self.post_processing

        # Create figure and axis for animation
        fig = plt.figure()
        ax = fig.add_subplot()

        # Set title
        title = ax.set_title("Post-processing image data 'fluor' at time index 0")

        @no_type_check
        def update(frame: int):
            """Update function for animation"""
            img_metadata = post_processing.image_metadata[image_index]
            image_data = post_processing.read_image_data(image_metadata=img_metadata, time_index=frame)
            img_plot = ax.imshow(image_data)
            # img_plot.set_data(image_data)  # Update image
            title.set_text(f"Post-processing image data 'fluor' at time index {frame}")
            plt.show()
            return (img_plot,)

        # Create the animation
        return animation.FuncAnimation(fig, update, frames=self.num_timepoints, interval=interval, blit=False)

    @no_type_check
    def animate_image(self, image_index: int) -> animation.FuncAnimation:
        return self.get_image_animation(image_index)

    def plot_averages(self) -> None:
        var_averages: set[VariableInfo] = {var for var in self.post_processing.variables if var.statistic_type == 0}
        # display(type(var_averages))
        # display(type(var_averages[0]))
        series_arrays = []
        series_legend = []
        times = self.post_processing.times
        # add envelope plot for each variable
        for var_average in var_averages:
            series_arrays.append(self.post_processing.statistics[:, var_average.var_index, [0, 2, 3]])
            series_legend.append(f"{var_average.var_name} [{var_average.stat_var_unit}]")

        # each series_array has 3 columns: mean, min, max
        # plot each series on a different plot arranged in a 2x2 grid with a legend from series_legends
        n_data = len(series_arrays)
        fig, ax = plt.subplots(n_data, n_data, figsize=(10, 10))
        for i, series_array in enumerate(series_arrays):
            ax[int(i / 2), i % 2].plot(times, series_array[:, 0], label="mean")
            ax[int(i / 2), i % 2].fill_between(times, series_array[:, 1], series_array[:, 2], alpha=0.2)
            ax[int(i / 2), i % 2].set_title(series_legend[i])
            ax[int(i / 2), i % 2].legend()

        return plt.show()
