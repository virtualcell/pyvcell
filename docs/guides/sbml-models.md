# Working with SBML

This guide covers loading, running, and converting SBML Spatial models with pyvcell.

## Prerequisites

- pyvcell installed (`pip install pyvcell`)
- An SBML Spatial model file (`.sbml`)

## Load and run an SBML Spatial model

pyvcell can run SBML Spatial models directly using `SbmlSpatialModel` and `SbmlSpatialSimulation`:

```python
from pathlib import Path
from pyvcell.sbml.sbml_simulation import SbmlSpatialSimulation
from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel

model_fp = Path("path/to/model.sbml")

# Load the SBML model
spatial_model = SbmlSpatialModel(filepath=model_fp)
spatial_model.copy_parameters()

# Create and run a simulation
simulation = SbmlSpatialSimulation(sbml_model=spatial_model)
result = simulation.run()
```

## Visualize SBML results

The result object has the same plotting API as VCML simulations:

```python
# 2D slice at a specific z-index
result.plotter.plot_slice_2d(time_index=3, channel_name="s0", z_index=5)

# 3D volume slice
result.plotter.plot_slice_3d(time_index=3, channel_id="s1")

# Concentration time series
result.plotter.plot_concentrations()
```

## Clean up

```python
simulation.cleanup()
```

## Convert between SBML and VCML

### SBML to VCML

Load an SBML file as a VCell Biomodel for further editing:

```python
import pyvcell.vcml as vc

# From file
biomodel = vc.load_sbml_file("model.sbml")

# From string
with open("model.sbml") as f:
    biomodel = vc.load_sbml_str(f.read())

# From URL
biomodel = vc.load_sbml_url("https://example.com/model.sbml")
```

### VCML to SBML

Export a VCell application as SBML:

```python
import pyvcell.vcml as vc

biomodel = vc.load_vcml_file("model.vcml")

# Export to SBML string
sbml_str = vc.to_sbml_str(bio_model=biomodel, application_name="app1")

# Write to file
vc.write_sbml_file(bio_model=biomodel, application_name="app1", filepath="exported.sbml")
```

## Convert between Antimony and SBML/VCML

Antimony provides a human-readable format that pyvcell converts through SBML:

```python
import pyvcell.vcml as vc

# Load Antimony as a Biomodel
biomodel = vc.load_antimony_str("""
    compartment cell = 1;
    species A in cell;
    species B in cell;
    J0: A -> B; k1*A
    k1 = 0.1; A = 10
""")

# Export back to Antimony
antimony_str = vc.to_antimony_str(bio_model=biomodel, application_name="app1")
```

## Complete example

```python
from pathlib import Path
from pyvcell.sbml.sbml_simulation import SbmlSpatialSimulation
from pyvcell.sbml.sbml_spatial_model import SbmlSpatialModel

# Load and run
spatial_model = SbmlSpatialModel(filepath=Path("model.sbml"))
spatial_model.copy_parameters()
simulation = SbmlSpatialSimulation(sbml_model=spatial_model)
result = simulation.run()

# Visualize
result.plotter.plot_concentrations()
result.plotter.plot_slice_3d(time_index=3, channel_id="s1")

# Clean up
simulation.cleanup()
```

!!! tip "Interactive notebook"
See the [sbml_workflow notebook](https://github.com/virtualcell/pyvcell/blob/main/examples/notebooks/sbml_workflow.ipynb) for a runnable version.

## Next steps

- [Building a Model](building-a-model.md) — Create models from Antimony with custom geometries
- [Visualization & Analysis](visualization.md) — Full plotting guide
