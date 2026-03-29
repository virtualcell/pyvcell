"""Demo: use synthetic microscopy image data as initial conditions for a spatial simulation."""

import matplotlib

matplotlib.use("Agg")

import numpy as np
from scipy.ndimage import gaussian_filter

import pyvcell.vcml as vc

# Load model — Tutorial_MultiApp_PDE has ec, cytosol, and Nucleus domains
biomodel = vc.load_vcml_file("examples/models/Tutorial_MultiApp_PDE.vcml")
app = biomodel.applications[0]
sim = app.simulations[0]
sim.mesh_size = (100, 100, 36)
sim.duration = 2.0
sim.output_time_step = 0.2

# Build a synthetic "microscopy image" from the geometry's cytosol domain mask
seg = app.geometry.to_segmented_image(resolution=64)
mask = seg.get_mask("cytosol").astype(float)
image_data = gaussian_filter(mask, sigma=3) + 0.05 * np.random.randn(*mask.shape)

# Create a field and use it as initial condition for Ran_cyt
field = vc.Field(data_name="microscopy", data_nD=image_data)
app.get_species_mapping("Ran_cyt").init_conc = field.expression

# Simulate — solver resamples 64^3 field data to 30^3 simulation mesh via trilinear interpolation
result = vc.simulate(biomodel, sim.name, fields=[field])

# Show results
print(f"Time points: {result.time_points}")
print(f"Channels: {[c.label for c in result.channel_data]}")
result.plotter.plot_concentrations()
result.plotter.plot_slice_3d(time_index=0, channel_id="Ran_cyt")
