# Quick Start

This guide walks you through loading a VCML model, running a simulation, and visualizing results.

## Load a VCML model

```python
import pyvcell.vcml as vc

biomodel = vc.load_vcml_file("path/to/model.vcml")
print(biomodel)
```

You can also load public models directly from the VCell database by ID:

```python
biomodel = vc.load_biomodel("279851639")
```

To browse or search models by name, authenticate first:

```python
from pyvcell._internal.api.vcell_client.auth.auth_utils import login_interactive

api_client = login_interactive()  # opens a browser for login

# List available models (public, shared, and your private models)
for m in vc.list_biomodels(api_client=api_client)[:2]:
    print(m)

# Load by name and owner
biomodel = vc.load_biomodel(name="Tutorial_MultiApp", owner="tutorial", api_client=api_client)

# Load by database ID
biomodel = vc.load_biomodel("279851639", api_client=api_client)
```

Output:

```
{'id': '117367327', 'name': ' Design dose in mammal MTB37rv', 'owner': 'mcgama88'}
{'id': '102571573', 'name': ' Zika- denge differential test to fetus x 1', 'owner': 'mcgama88'}
```

Or from a URL:

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
