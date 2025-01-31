import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import zarr
from IPython.display import HTML
from matplotlib import animation

from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.postprocessing import PostProcessing
from pyvcell.simdata.simdata_models import PdeDataSet, DataFunctions
from pyvcell.simdata.zarr_writer import write_zarr
from pyvcell.solvers.fvsolver import solve as fvsolve


class Result(object):
    def __init__(self, solver_output_dir: Path, sim_id: int, job_id: int):
        self.solver_output_dir = solver_output_dir
        self.zarr_dir = self.solver_output_dir / "zarr"
        self.sim_id = sim_id
        self.job_id = job_id

    @property
    def dataset(self):
        return zarr.open(str(self.zarr_dir), mode='r')

    @property
    def metadata(self):
        return self.dataset.attrs.asdict()['metadata']

    @property
    def post_processing(self):
        post_processing = PostProcessing(postprocessing_hdf5_path=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.hdf5")
        post_processing.read()
        return post_processing

    @property
    def concentrations(self):
        return [c['mean_values'] for c in self.metadata['channels'] if c['index'] > 0]

    @property
    def channels(self):
        return self.metadata['channels']

    def get_channel_ids(self) -> List[str]:
        ids = []
        for i, channel in enumerate(self.channels):
            name = self.channels[i]['domain_name']
            ids.append(name)
        return ids

    def get_time_axis(self, time_index: int = None):
        """
        Get x-axis data of times specified by `time_index`.
        """
        times = self.metadata['times']
        return times[time_index] if time_index is not None else times

    def slice_dataset(self, time_index: int, channel_index: int, z_index: int):
        ds = self.dataset
        return ds[time_index, channel_index, z_index, :, :]

    def plot_concentrations(self):
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

    def plot_slice_2d(self, time_index: int, channel_index: int, z_index: int):
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

    def plot_slice_3d(self, time_index, channel_index):
        # Select a 3D volume for a single time point and channel, shape is (z, y, x)
        metadata = self.metadata
        channel_domain = metadata['channels'][channel_index]['domain_name']
        volume = self.dataset[time_index, channel_index, :, :, :]

        # Create a figure for 3D plotting
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Define a mask to display the volume (use 'region_mask' channel)
        mask = np.copy(self.dataset[3, 0, :, :, :])
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
        ax.set_zlabel('Z')

        # Show the plot
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

    def get_3d_slice_animation(self, channel_index, interval=200) -> animation.FuncAnimation:
        """
        Animate the 3D scatter plot over time.

        Parameters:
            channel_index (int): The index of the channel to visualize.
            interval (int): Time interval between frames in milliseconds.
        """
        # Extract metadata and the number of time points
        metadata = self.metadata
        channel_domain = metadata['channels'][channel_index]['domain_name']
        num_timepoints = self.dataset.shape[0]  # Assuming time is first dimension

        # Create a figure for 3D plotting
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Set labels for axes
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        sc = None

        def update(frame: int):
            """ Update function for animation """
            # Define a mask to display the volume (use 'region_mask' channel)
            mask = np.copy(self.dataset[frame, 0, :, :, :])
            z, y, x = np.where(mask == 1)

            volume = self.dataset[frame, channel_index, :, :, :]
            intensities = volume[z, y, x]

            # Initialize the scatter plot with empty data
            scatter = ax.scatter(x, y, z, c=intensities, cmap='viridis')
            ax.set_title(f"Channel: {channel_domain}, Time Index: {frame}")
            sc = scatter
            return scatter,

        # Create the animation
        fig.colorbar(sc, ax=ax, label='Intensity')
        ani = animation.FuncAnimation(fig, update, num_timepoints, interval=interval, blit=False)

        return ani

    def render_3d_slice_animation(self, channel_index, interval=200) -> HTML:
        ani = self.get_3d_slice_animation(channel_index, interval)
        return HTML(ani.to_jshtml())

