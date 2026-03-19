# Field Data Workflows

Field data lets you use results from one simulation as initial conditions for another, or supply synthetic data (e.g., from images) as initial conditions. This guide covers both patterns.

## Prerequisites

- pyvcell installed (`pip install pyvcell`)
- Familiarity with [Building a Model](building-a-model.md)

## Concept: vcField references

In VCell, the `vcField()` function references external data in species initial condition expressions:

```
vcField('dataset_name', 'variable_name', time, 'Volume')
```

- **dataset_name** — identifier for the field data source
- **variable_name** — which variable to read from the dataset
- **time** — the time point to sample
- **Volume** — the domain type

## Chain simulations using field data

Run one simulation, then use its output as initial conditions for a second run.

### Step 1: Load a model and run the first simulation

```python
import pyvcell.vcml as vc

biomodel = vc.load_vcml_file("path/to/model.vcml")
app = biomodel.applications[0]

# Set initial conditions for the first run
s0_mapping = next(s for s in app.species_mappings if s.species_name == "s0")
s1_mapping = next(s for s in app.species_mappings if s.species_name == "s1")
s0_mapping.init_conc = "3+sin(x)+cos(y)+sin(z)"
s1_mapping.init_conc = "3+sin(x+y+z)"

sim = app.add_sim(name="sim1", duration=10.0, output_time_step=0.1, mesh_size=(20, 20, 20))

# Run first simulation
sim1_result = vc.simulate(biomodel=biomodel, simulation=sim.name)
sim1_dirname = sim1_result.solver_output_dir.name
```

### Step 2: Reference first simulation's output

Use `vcField()` to set initial conditions from the first run:

```python
# Use s0 * s1 from the first simulation at t=0 as the new initial condition for s0
s0_mapping.init_conc = (
    f"vcField('{sim1_dirname}','s0',0.0,'Volume') * "
    f"vcField('{sim1_dirname}','s1',0.0,'Volume')"
)
s1_mapping.init_conc = "5.0"

# Run second simulation
sim2_result = vc.simulate(biomodel=biomodel, simulation=sim.name)
```

### Step 3: Visualize both runs

```python
# First simulation
sim1_result.plotter.plot_slice_3d(time_index=0, channel_id="s0")
sim1_result.plotter.plot_concentrations()

# Second simulation
sim2_result.plotter.plot_slice_3d(time_index=0, channel_id="s0")
sim2_result.plotter.plot_concentrations()

# Clean up
sim2_result.cleanup()
```

## Synthetic field data from images

You can also create field data programmatically (e.g., from microscopy images or synthetic functions) and supply it to a simulation.

### Step 1: Set up vcField references

```python
import pyvcell.vcml as vc

biomodel = vc.load_vcml_file("path/to/model.vcml")
app = biomodel.applications[0]

s0_mapping = next(s for s in app.species_mappings if s.species_name == "s0")
s1_mapping = next(s for s in app.species_mappings if s.species_name == "s1")

# Reference external field data by name
s0_mapping.init_conc = "vcField('my_dataset', 'species0', 0.5, 'Volume')"
s1_mapping.init_conc = "vcField('checkerboard', 'v', 0.0, 'Volume')"

sim = app.add_sim(name="sim1", duration=10.0, output_time_step=0.1, mesh_size=(20, 20, 20))
```

### Step 2: Create Field objects

Use `Field.create_fields()` to generate template Field objects from the model's `vcField` references, then populate them with custom data:

```python
import numpy as np
from pyvcell._internal.simdata.mesh import CartesianMesh

# Create empty fields matching the vcField references
fields = vc.Field.create_fields(bio_model=biomodel, sim=sim)

# Generate coordinate arrays for the mesh
shape = fields[0].data_nD.shape
coords = CartesianMesh.compute_coordinates(
    mesh_shape=(shape[0], shape[1], shape[2]),
    origin=app.geometry.origin,
    extent=app.geometry.extent,
)

# Fill with synthetic data
fields[0].data_nD = np.cos(0.5 * coords[:,:,:,0]) * np.sin(0.5 * coords[:,:,:,1]) * 8.0
fields[1].data_nD = np.cos(0.3 * coords[:,:,:,0]) * np.sin(0.3 * coords[:,:,:,1]) * 4.0
```

### Step 3: Run the simulation with field data

Pass the `fields` argument to `simulate()`:

```python
result = vc.simulate(biomodel=biomodel, simulation=sim, fields=fields)
result.plotter.plot_slice_3d(time_index=0, channel_id="s0")
result.plotter.plot_concentrations()
```

## Complete example: chaining simulations

```python
import pyvcell.vcml as vc

biomodel = vc.load_vcml_file("model.vcml")
app = biomodel.applications[0]
s0 = next(s for s in app.species_mappings if s.species_name == "s0")
s1 = next(s for s in app.species_mappings if s.species_name == "s1")

# First run
s0.init_conc = "3+sin(x)+cos(y)+sin(z)"
s1.init_conc = "3+sin(x+y+z)"
sim = app.add_sim(name="sim1", duration=10.0, output_time_step=0.1, mesh_size=(20, 20, 20))
result1 = vc.simulate(biomodel=biomodel, simulation=sim.name)

# Second run using first run's output
dirname = result1.solver_output_dir.name
s0.init_conc = f"vcField('{dirname}','s0',0.0,'Volume') * vcField('{dirname}','s1',0.0,'Volume')"
s1.init_conc = "5.0"
result2 = vc.simulate(biomodel=biomodel, simulation=sim.name)

# Compare
result1.plotter.plot_concentrations()
result2.plotter.plot_concentrations()
```

!!! tip "Example scripts"
See [`fielddata_from_sim_workflow.py`](https://github.com/virtualcell/pyvcell/blob/main/examples/scripts/fielddata_from_sim_workflow.py) and [`fielddata_from_image_workflow.py`](https://github.com/virtualcell/pyvcell/blob/main/examples/scripts/fielddata_from_image_workflow.py) for complete runnable examples.

## Next steps

- [Visualization & Analysis](visualization.md) — Full plotting and animation guide
- [Parameter Exploration](parameter-exploration.md) — Batch parameter sweeps
