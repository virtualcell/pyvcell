import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import numpy as np
import zarr

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

        self.dataset = self.get_dataset()
        self.metadata = self.get_metadata()

    def get_dataset(self, zarr_dir=None) -> zarr.Array | zarr.Group:
        return zarr.open(zarr_dir or self.zarr_dir, mode='r')

    def get_metadata(self, dataset=None):
        ds = dataset or self.dataset
        return ds.attrs.asdict()['metadata']

    def get_post_processing(self) -> PostProcessing:
        post_processing = PostProcessing(postprocessing_hdf5_path=self.solver_output_dir / f"SimID_{self.sim_id}_{self.job_id}_.hdf5")
        post_processing.read()
        return post_processing

    def get_concentrations(self):
        metadata = self.get_metadata()
        return [c['mean_values'] for c in metadata['channels'] if c['index'] > 0]

    def slice_dataset(self, time_index: int, channel_index: int, z_index: int, dataset: zarr.Array | zarr.Group = None):
        ds = dataset or self.dataset
        return ds[time_index, channel_index, z_index, :, :]

    def plot_concentrations(self):
        metadata = self.get_metadata()
        t = metadata['times']
        y_labels = [c['label'] for c in metadata['channels'] if c['index'] > 0]
        y = self.get_concentrations()

        fig, ax = plt.subplots()
        ax.plot(t, y)
        ax.set(xlabel='time (s)', ylabel='concentration',
               title='Concentration over time')
        ax.legend(y_labels)
        ax.grid()

    def plot_slice_2d(self, time_index: int, channel_index: int, z_index: int):
        data_slice = self.slice_dataset(time_index, channel_index, z_index)

        metadata = self.get_metadata()
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
        metadata = self.get_metadata()
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
