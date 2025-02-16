import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Union, TypedDict, Any, Optional, no_type_check

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import zarr  # type: ignore
import pyvista as pv
from IPython.display import HTML
from matplotlib import animation

# from pyvcell.data_model.dataset import Metadata
from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.postprocessing import PostProcessing
from pyvcell.simdata.simdata_models import PdeDataSet, DataFunctions
from pyvcell.simdata.vtk.fv_mesh_mapping import from_mesh_data
from pyvcell.simdata.vtk.vismesh import VisMesh
from pyvcell.simdata.zarr_writer import write_zarr
from pyvcell.solvers.fvsolver import solve as fvsolve


class Result(object):
    def __init__(self, solver_output_dir: Path, sim_id: int, job_id: int):
        self.solver_output_dir = solver_output_dir
        self.zarr_dir = self.solver_output_dir / "zarr"
        self.sim_id = sim_id
        self.job_id = job_id

    def get_dataset(self, ds_type: str = 'zarr') -> Union[zarr.Group, zarr.Array, PdeDataSet]:
        if ds_type == "zarr":
            return self.zarr_dataset
        else:
            return self.pde_dataset

    @property
    def dataset(self) -> Union[zarr.Group, zarr.Array, PdeDataSet]:
        # return zarr.open(str(self.zarr_dir), mode='r')
        return self.get_dataset()

    @property
    def zarr_dataset(self) -> Union[zarr.Group, zarr.Array]:
        return zarr.open(str(self.zarr_dir), mode='r')

    @property
    def pde_dataset(self) -> PdeDataSet:
        return self._get_pde_dataset()

    @property
    def metadata(self) -> Any:
        return self.zarr_dataset.attrs.asdict()['metadata']

    @property
    def post_processing(self) -> PostProcessing:
        post_processing = PostProcessing(postprocessing_hdf5_path=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.hdf5")
        post_processing.read()
        return post_processing

    @property
    def concentrations(self) -> list[float]:
        return [c['mean_values'] for c in self.metadata['channels'] if c['index'] > 0]

    @property
    def channels(self) -> Union[Any, list[Any]]:
        return self.metadata['channels']

    @property
    def num_timepoints(self) -> Union[int, Any]:
        return self.zarr_dataset.shape[0]  # Assuming time is first dimension

    @property
    def cartesian_mesh(self) -> CartesianMesh:
        return self._get_mesh()

    def get_channel_ids(self) -> list[str]:
        ids = []
        for i, channel in enumerate(self.channels):
            name = self.channels[i]['domain_name']
            ids.append(name)
        return ids

    def get_time_axis(self, time_index: Optional[int] = None) -> Union[list[list[float]], list[float], Any]:
        """
        Get x-axis data of times specified by `time_index`.
        """
        times = self.metadata['times']
        return times[time_index] if time_index is not None else times

    def slice_dataset(self, time_index: int, channel_index: int, z_index: int) -> Union[np.ndarray[Any, Any], Any]:
        ds = self.zarr_dataset
        return ds[time_index, channel_index, z_index, :, :].tolist()

    def plot_concentrations(self) -> None:
        t = self.get_time_axis()

        fig, ax = plt.subplots()
        ax.plot(t, self.concentrations)
        ax.set(
            xlabel='time (s)',
            ylabel='concentration',
            title='Concentration over time'
        )

        y_labels = [c['label'] for c in self.metadata['channels'] if c['index'] > 0]
        ax.legend(y_labels)
        ax.grid()

    def plot_slice_2d(self, time_index: int, channel_index: int, z_index: int) -> None:
        data_slice = self.slice_dataset(time_index, channel_index, z_index)

        metadata = self.metadata
        t = metadata['times'][time_index]
        channel_label = metadata['channels'][channel_index]['label']
        channel_domain = metadata['channels'][channel_index]['domain_name']
        title = f"{channel_label} (in {channel_domain}) at t={t}, slice z={z_index}"

        # Display the slice as an image
        plt.imshow(data_slice)
        plt.title(title)
        return plt.show()

    def plot_slice_3d(self, time_index: int, channel_index: int) -> None:
        # Select a 3D volume for a single time point and channel, shape is (z, y, x)
        metadata = self.metadata
        channel_domain = metadata['channels'][channel_index]['domain_name']
        volume = self.zarr_dataset[time_index, channel_index, :, :, :]

        # Create a figure for 3D plotting
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Define a mask to display the volume (use 'region_mask' channel)
        mask = np.copy(self.zarr_dataset[3, 0, :, :, :])
        z, y, x = np.where(mask == 1)

        # Get the intensity values for these points
        intensities = volume[z, y, x]

        # Create a 3D scatter plot
        scatter = ax.scatter(x, y, z, c=intensities, cmap='viridis')

        # Add a color bar to represent intensities
        fig.colorbar(scatter, ax=ax, label='Intensity')

        # Set labels for axes
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')  # type: ignore

        # Show the plot
        return plt.show()

    def plot_image(self, image_index: int, time_index: int) -> None:
        # display image dataset "fluor" at time index 4 as an image
        img_metadata = self.post_processing.image_metadata[image_index]
        image_data: np.ndarray = self.post_processing.read_image_data(image_metadata=img_metadata, time_index=time_index)  # type: ignore
        plt.imshow(image_data)
        plt.title(f"post processing image data '{img_metadata.name}' at time index {time_index}")
        return plt.show()

    def _to_zarr(self) -> None:
        pde_dataset = self._get_pde_dataset()
        data_functions = self._get_data_functions()
        mesh = self._get_mesh()
        return write_zarr(pde_dataset=pde_dataset, data_functions=data_functions, mesh=mesh, zarr_dir=self.zarr_dir)

    def _get_pde_dataset(self) -> PdeDataSet:
        pde_dataset = PdeDataSet(base_dir=self.solver_output_dir, log_filename=f"SimID_{self.sim_id}_{self.job_id}_.log")
        pde_dataset.read()
        return pde_dataset

    def _get_data_functions(self) -> DataFunctions:
        data_functions = DataFunctions(function_file=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.functions")
        data_functions.read()
        return data_functions

    def _get_mesh(self) -> CartesianMesh:
        mesh = CartesianMesh(mesh_file=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.mesh")
        mesh.read()
        return mesh

    def get_3d_slice_animation(self, channel_index: int, interval: int = 200) -> animation.FuncAnimation:
        """
        Animate the 3D scatter plot over time.

        Parameters:
            channel_index (int): The index of the channel to visualize.
            interval (int): Time interval between frames in milliseconds.
        """
        # Extract metadata and the number of time points
        metadata = self.metadata
        channel_domain = metadata['channels'][channel_index]['domain_name']
        num_timepoints = self.num_timepoints

        # Create a figure for 3D plotting
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Set labels for axes
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')  # type: ignore
        sc = None

        @no_type_check
        def update(frame: int):
            """ Update function for animation """
            # Define a mask to display the volume (use 'region_mask' channel)
            mask = np.copy(self.zarr_dataset[frame, 0, :, :, :])
            z, y, x = np.where(mask == 1)

            volume = self.zarr_dataset[frame, channel_index, :, :, :]
            intensities = volume[z, y, x]

            # Initialize the scatter plot with empty data
            scatter = ax.scatter(x, y, z, c=intensities, cmap='viridis')
            ax.set_title(f"Channel: {channel_domain}, Time Index: {frame}")
            sc = scatter
            return scatter,

        # Create the animation
        fig.colorbar(sc, ax=ax, label='Intensity')  # type: ignore
        ani = animation.FuncAnimation(fig, update, num_timepoints, interval=interval, blit=False)

        return ani

    @no_type_check
    def render_animation(self, ani: animation.FuncAnimation) -> HTML:
        return HTML(ani.to_jshtml())

    def animate_channel_3d(self, channel_index: int) -> Any:
        ani = self.get_3d_slice_animation(channel_index)
        return self.render_animation(ani)

    def get_image_animation(self, image_index: int, interval: int = 200) -> animation.FuncAnimation:
        """
        Animate the fluorescence image over time.

        Parameters:
            result: Object containing post-processing image data.
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
            """ Update function for animation """
            img_metadata = post_processing.image_metadata[image_index]
            image_data = post_processing.read_image_data(image_metadata=img_metadata, time_index=frame)
            img_plot = ax.imshow(image_data)
            # img_plot.set_data(image_data)  # Update image
            title.set_text(f"Post-processing image data 'fluor' at time index {frame}")
            plt.show()
            return img_plot,

        # Create the animation
        ani = animation.FuncAnimation(fig, update, frames=self.num_timepoints, interval=interval, blit=False)

        return ani

    @no_type_check
    def animate_image(self, image_index: int) -> HTML:
        ani = self.get_image_animation(image_index)
        return self.render_animation(ani)

    def to_vtk(self, domain_name: str, b_volume: bool = True) -> pv.UnstructuredGrid:
        vis_mesh: VisMesh = from_mesh_data(
            cartesian_mesh=self.cartesian_mesh,
            domain_name=domain_name,
            b_volume=b_volume
        )

        # derive points ([point.coords() for point in vis_mesh.points])
        points = [point.coords() for point in vis_mesh.points]

        # derive cells (range of n cells)
        cells = list(range(len(points)))

        # derive cell types
        cell_types = [pv.CellType.QUAD]

        # create unstructured grid
        return pv.UnstructuredGrid(cells, cell_types, points)

