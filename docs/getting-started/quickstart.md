# Quick Start

This guide walks you through loading a VCML model, running a simulation, and visualizing results.

## Load a VCML model

```python
import pyvcell.vcml as vc

biomodel = vc.load_vcml_file("path/to/model.vcml")
print(biomodel)
```

You can also load models from a URL:

```python
biomodel = vc.load_vcml_url(
    "https://raw.githubusercontent.com/virtualcell/pyvcell/refs/heads/main/"
    "examples/models/Tutorial_MultiApp_PDE.vcml"
)
```

Output:

```
Biomodel(model=Model(compartments=['cyt', 'nuc', 'EC', 'pm', 'nm'],
    species=['Ran_cyt', 'C_cyt', 'RanC_nuc', 'RanC_cyt'],
    reactions=['r0', 'flux0'], parameters=[]),
    applications=['3D pde'], simulations=['Simulation4'])
```

## Inspect the model

```python
model = biomodel.model

# List species and compartments
print(model.species_names)    # ['Ran_cyt', 'C_cyt', 'RanC_nuc', 'RanC_cyt']
print(model.compartment_names) # ['cyt', 'nuc', 'EC', 'pm', 'nm']

# View parameters
print(model.parameter_values)
```

## Run a simulation

Every biomodel contains one or more applications, each with simulations:

```python
# List available simulations
print(biomodel.simulation_names)  # ['Simulation4']

# Run the simulation
result = vc.simulate(biomodel, "Simulation4")
```

## Visualize results

```python
# Plot mean concentrations over time
result.plotter.plot_concentrations()

# Plot a 3D slice at a specific time point
result.plotter.plot_slice_3d(time_index=3, channel_id="Ran_cyt")

# Plot a 2D slice
result.plotter.plot_slice_2d(time_index=0, channel_name="Ran_cyt", z_index=5)
```

## Access raw data

Results are stored as Zarr arrays, accessible as NumPy arrays:

```python
# Time points
print(result.time_points)

# Channel labels
print([c.label for c in result.channel_data])

# Get a 3D data slice for a specific channel and time
data = result.get_slice("Ran_cyt", time_index=3)
print(data.shape)
```

## Clean up

Simulation output is stored in the workspace directory. To remove a specific result:

```python
result.cleanup()
```

## Complete example

```python
import pyvcell.vcml as vc

# Load model from URL
biomodel = vc.load_vcml_url(
    "https://raw.githubusercontent.com/virtualcell/pyvcell/refs/heads/main/"
    "examples/models/Tutorial_MultiApp_PDE.vcml"
)

# Run simulation
result = vc.simulate(biomodel, "Simulation4")

# Visualize
result.plotter.plot_concentrations()
result.plotter.plot_slice_3d(time_index=3, channel_id="Ran_cyt")

# Clean up
result.cleanup()
```

## Next steps

- [Building a Model](../guides/building-a-model.md) — Create a model from scratch using Antimony
- [Working with SBML](../guides/sbml-models.md) — Load and simulate SBML spatial models
- [Visualization & Analysis](../guides/visualization.md) — Full guide to plotting and 3D visualization
