# pyvcell

[![Release](https://img.shields.io/github/v/release/virtualcell/pyvcell)](https://img.shields.io/github/v/release/virtualcell/pyvcell)
[![Build status](https://img.shields.io/github/actions/workflow/status/virtualcell/pyvcell/main.yml?branch=main)](https://github.com/virtualcell/pyvcell/actions/workflows/main.yml?query=branch%3Amain)
[![License](https://img.shields.io/github/license/virtualcell/pyvcell)](https://img.shields.io/github/license/virtualcell/pyvcell)

**pyvcell** is the Python interface for [Virtual Cell](https://vcell.org) — enabling spatial modeling, simulation, and analysis of cell biological systems directly from Python.

## What you can do

- **Define models** from Antimony, SBML, or VCML, or build them programmatically
- **Create geometries** — analytic shapes, multi-compartment, or image-based
- **Run spatial simulations** locally using the VCell finite volume solver
- **Analyze results** — time-series statistics, spatiotemporal arrays (Zarr/NumPy), 3D mesh data (VTK)
- **Visualize** — built-in plotting (Matplotlib), 3D rendering (VTK/PyVista), interactive widgets (Trame)

## Quick example

```python
import pyvcell.vcml as vc

# Load a model and simulate
biomodel = vc.load_vcml_file("model.vcml")
result = vc.simulate(biomodel, "sim1")

# Plot results
result.plotter.plot_concentrations()
result.plotter.plot_slice_3d(time_index=3, channel_id="s1")
```

## Getting started

<div class="grid cards" markdown>

- **[Installation](getting-started/installation.md)** — Install pyvcell and set up your environment
- **[Quick Start](getting-started/quickstart.md)** — Load a model, run a simulation, and plot results

</div>

## Guides

| Guide | Description |
|-------|-------------|
| [Building a Model](guides/building-a-model.md) | Define reactions in Antimony, create geometry, simulate |
| [Working with SBML](guides/sbml-models.md) | Load and run SBML spatial models |
| [Complex Geometries](guides/complex-geometries.md) | Multi-compartment and reusable geometries |
| [Parameter Exploration](guides/parameter-exploration.md) | Batch parameter sampling and sensitivity analysis |
| [Field Data Workflows](guides/field-data.md) | Chain simulations using field data as initial conditions |
| [Visualization & Analysis](guides/visualization.md) | Plotting, 3D slices, animations, and Trame widgets |

## API Reference

| Module | Contents |
|--------|----------|
| [Models](reference/models.md) | Biomodel, Model, Species, Compartment, Reaction, Geometry, Application, Simulation |
| [I/O Functions](reference/io.md) | Load/write VCML, SBML, and Antimony |
| [Simulation & Results](reference/simulation.md) | simulate(), Result, Plotter, VtkData, Field |

## Example notebooks

Interactive notebooks are available in the [`examples/notebooks/`](https://github.com/virtualcell/pyvcell/tree/main/examples/notebooks) directory:

- [Antimony model building](https://github.com/virtualcell/pyvcell/blob/main/examples/notebooks/sysbio-1-antimony.ipynb) — Define a model from Antimony and simulate
- [Parameter exploration](https://github.com/virtualcell/pyvcell/blob/main/examples/notebooks/sysbio-2-params.ipynb) — Batch runs with random parameter sampling
- [Geometry import](https://github.com/virtualcell/pyvcell/blob/main/examples/notebooks/sysbio-3-geometry.ipynb) — Multi-compartment geometry from existing models
- [SBML workflow](https://github.com/virtualcell/pyvcell/blob/main/examples/notebooks/sbml_workflow.ipynb) — Load and run SBML spatial models
