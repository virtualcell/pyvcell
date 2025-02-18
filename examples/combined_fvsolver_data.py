import os
import shutil
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import zarr  # type: ignore[import-untyped]
from IPython.display import display

from pyvcell.simdata.mesh import CartesianMesh
from pyvcell.simdata.postprocessing import PostProcessing
from pyvcell.simdata.simdata_models import DataFunctions, PdeDataSet
from pyvcell.simdata.zarr_writer import write_zarr
from pyvcell.solvers.fvsolver import solve as fvsolve

# # Run a VCell PDE simulation from solver input files
# 1. Copy all files from solver_input directory to a temporary directory for solving
# 2. prepare empty solver output directory, copying in the functions file
# 2. Execute the Finite Volume PDE solver


# move all files from solver_input directory to a temporary directory for solving
temp_solver_dir = Path(tempfile.mkdtemp(prefix="pyvcell_test_data_"))
solver_input_dir = Path(os.getcwd()) / "solver_input"
for file in solver_input_dir.iterdir():
    print(file)
    shutil.copy(file, temp_solver_dir)

fv_input_file = temp_solver_dir / "SimID_946368938_0_.fvinput"
vcg_file = temp_solver_dir / "SimID_946368938_0_.vcg"
functions_file = temp_solver_dir / "SimID_946368938_0_.functions"


os.path.exists(solver_input_dir)

solver_output_dir = Path(os.getcwd()) / "test_output"

# clear contents of solver_output_dir
for file in solver_output_dir.iterdir():
    if file.is_file() and not file.name.startswith("."):
        file.unlink()

# copy functions file to solver_output_dir
shutil.copy(functions_file, solver_output_dir)

# execute Finite Volume PDE solver
ret_code = fvsolve(input_file=fv_input_file, vcg_file=vcg_file, output_dir=solver_output_dir)
if ret_code != 0:
    raise ValueError(f"Solver failed with return code {ret_code}")


# ## extract the vcell simulation dataset from the tarball (compressed to save space)

# ## read vcell simulation results metadata
# * `PdeDataSet` contains the metadata for the tabular simulation results (e.g. state variables, shape, time points)
# * `DataFunctions` contains the function definitions (name, expression, type, domain)
# ![vcell simulation results](./example_vcell_ui.png)

sim_id = 946368938
job_id = 0
pde_dataset = PdeDataSet(base_dir=solver_output_dir, log_filename=f"SimID_{sim_id}_{job_id}_.log")
pde_dataset.read()
data_functions = DataFunctions(function_file=solver_output_dir / f"SimID_{sim_id}_{job_id}_.functions")
data_functions.read()
mesh = CartesianMesh(mesh_file=solver_output_dir / f"SimID_{sim_id}_{job_id}_.mesh")
mesh.read()
post_processing = PostProcessing(postprocessing_hdf5_path=solver_output_dir / f"SimID_{sim_id}_{job_id}_.hdf5")
post_processing.read()


# ## write the vcell simulation dataset to zarr including:
# * metadata
# * numerical datasets from stored data and evaluated functions
# * ... masks for domains coming soon (e.g. cell, extracellular, etc.)

write_zarr(pde_dataset=pde_dataset, data_functions=data_functions, mesh=mesh, zarr_dir=solver_output_dir / "zarr")


# ## Open and display slices from the zarr dataset as an image
# * no masking for domains
# * different colormap and scaling

# Open the Zarr dataset
dataset = zarr.open(solver_output_dir / "zarr", mode="r")
metadata = dataset.attrs.asdict()["metadata"]
display(f"shape = {dataset.shape}")  # type: ignore[no-untyped-call]
display(metadata)  # type: ignore[no-untyped-call]

# Get a slice of the dataset, shape is (time, channel, z, y, x)
channel_index = 2
z_index = 9
time_index = 3
data_slice = dataset[time_index, channel_index, z_index, :, :]
channel_label = metadata["channels"][channel_index]["label"]
channel_domain = metadata["channels"][channel_index]["domain_name"]
t = metadata["times"][time_index]
title = f"{channel_label} (in {channel_domain}) at t={t}, slice z={z_index}"

# Display the slice as an image
plt.imshow(data_slice)
plt.title(title)
plt.show()


# Select a 3D volume for a single time point and channel, shape is (z, y, x)
channel_index = 2
time_index = 3
channel_domain = metadata["channels"][channel_index]["domain_name"]
volume = dataset[time_index, channel_index, :, :, :]

# Create a figure for 3D plotting
fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")

# Define a mask to display the volume (use 'region_mask' channel)
mask = np.copy(dataset[3, 0, :, :, :])
mask_z, mask_y, mask_x = np.where(mask == 1)

# Get the intensity values for these points
intensities = volume[mask_z, mask_y, mask_x]

# Create a 3D scatter plot
scatter = ax.scatter(mask_x, mask_y, mask_z, c=intensities, cmap="viridis")

# Add a color bar to represent intensities
fig.colorbar(scatter, ax=ax, label="Intensity")

# Set labels for axes
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")  # type: ignore[attr-defined]

# Show the plot
plt.show()


print(dataset[time_index, channel_index, :, :, :].shape)


t = metadata["times"]
y = [c["mean_values"] for c in metadata["channels"] if c["index"] > 4]
y_labels = [c["label"] for c in metadata["channels"] if c["index"] > 4]

fig, ax = plt.subplots()
ax.plot(t, np.array(y).T.tolist())
ax.set(xlabel="time (s)", ylabel="concentration", title="Concentration over time")
ax.legend(y_labels)
ax.grid()


# ## Open and display slices from the post processing dataset as an image

# display image dataset "fluor" at time index 4 as an image
fluorescence = post_processing.image_metadata[0]
image_data: np.typing.NDArray[np.float64] = post_processing.read_image_data(image_metadata=fluorescence, time_index=4)
plt.imshow(image_data)
plt.title("post processing image data 'fluor' at time index 4")
plt.show()


# ## Open and display Variable Statistics from the post processing dataset

print(post_processing.variables[0].stat_var_unit)


var_averages = list({var for var in post_processing.variables if var.statistic_type == 0})
display(type(var_averages))  # type: ignore[no-untyped-call]
display(type(var_averages[0]))  # type: ignore[no-untyped-call]
series_arrays = []
series_legend = []
times = post_processing.times
# add envelope plot for each variable
for var_average in var_averages:
    series_arrays.append(post_processing.statistics[:, var_average.var_index, [0, 2, 3]])
    series_legend.append(f"{var_average.var_name} [{var_average.stat_var_unit}]")

# each series_array has 3 columns: mean, min, max
# plot each series on a different plot arranged in a 2x2 grid with a legend from series_legends
fig, ax = plt.subplots(2, 2, figsize=(10, 10))
for i, series_array in enumerate(series_arrays):
    axis = ax[int(i / 2), i % 2]  # type: ignore[index]
    axis.plot(times, series_array[:, 0], label="mean")
    axis.fill_between(times, series_array[:, 1], series_array[:, 2], alpha=0.2)
    axis.set_title(series_legend[i])
    axis.legend()

plt.show()
