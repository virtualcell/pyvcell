# pyvcell — Project Overview

Source material for presentations, slides, and stakeholder communications.

## What it is

Python interface for [Virtual Cell](https://vcell.org) — a platform for spatial modeling, simulation, and analysis of cell biological systems. Published as prebuilt Python packages on PyPI for Linux, macOS, and Windows.

## Motivation

Jupyter notebooks have become a valuable tool for learning, developing, and disseminating modeling projects, and enhance reproducibility. Python scripting provides flexibility to customize simulation and data analysis workflows and easily integrate familiar, powerful tools for data analysis and visualization. Following the approach of the BasiCO Python library (which wraps COPASI), pyvcell empowers modelers to use VCell's spatial simulation technology while providing complete control over the structure of their modeling projects — all from Python scripts, Jupyter notebooks, or other third-party tools.

## Who it's for

Computational biologists, biophysicists, and researchers who want to build and simulate cell models programmatically rather than through the VCell desktop GUI. pyvcell expands the reach of VCell's spatial simulation capabilities to modelers who prefer Python-based workflows.

## Core capabilities

1. **Model building** — Define compartments, species, reactions, and spatial geometries in Python using Antimony, SBML, or VCML formats
2. **Complex geometries** — Analytic primitives (spheres, backgrounds), multi-compartment structures, reusable geometries from existing models, and image-based segmented geometries
3. **Local simulation** — Run VCell solvers locally, get results as Zarr arrays, visualize with built-in plotters
4. **Remote simulation** — Connect to the VCell server cluster for large-scale simulations, with results streamed back lazily
5. **Simulation chaining** — Use output from one simulation as initial conditions for the next via field data references (`vcField`)
6. **Synthetic field data** — Supply programmatic or image-derived spatial data as initial conditions
7. **Parameter exploration** — Modify parameters, run batch sweeps, and compare results for sensitivity analysis
8. **Visualization** — Concentration time series, 2D/3D spatial slices, animations, VTK mesh export, and interactive Trame widgets in Jupyter
9. **Format interop** — Round-trip between VCML, SBML Spatial (designed by the VCell team), and Antimony representations

## Key design principles

- **Lightweight Python datamodels, proven Java algorithms** — Model authoring and manipulation uses pure Python dataclasses exposing essential VCell concepts only. Validation, math generation, and simulation preprocessing invoke battle-tested Java logic from libvcell, bundled via GraalVM native compilation. This includes model translation (SBML Spatial to VCell BioModel), math generation (BioModel to MathModel using VCell's formal equation-based descriptions of reaction-diffusion-advection PDE, particle Brownian dynamics, hybrid PDE/particle, or rule-based mesoscopic molecular processes), and mesh generation/solver preprocessing.

- **Native solvers as Python packages** — VCell's C++ solvers are repackaged as standalone Python packages using thin wrappers (pybind11, scikit-build-core). pyvcell-fvsolver is on PyPI today; pyvcell-ode, pyvcell-nfsim, and pyvcell-stoch are in progress.

- **Wrapped API with session-based remote access** — All VCell API endpoints are accessible, but common operations (load/save biomodels, run remote simulations, retrieve results) are wrapped in a remote session for simplified, discoverable access. A single entry point (`vc.connect()`) provides both anonymous and authenticated sessions.

- **Cloud-native lazy data retrieval** — Remote results use N5 format (similar to Zarr) with TensorStore for multidimensional data access — only requested data is transmitted, on demand.

- **Ecosystem integration** — Results are exported into VTK and Zarr format for convenient access using NumPy, Pandas, VTK, and PyVista for further data analysis and visualization. Interactive 3D visualization in Jupyter is provided via Trame widgets.

## Minimal examples

### Local: load, simulate, visualize

```python
import pyvcell.vcml as vc

biomodel = vc.load_vcml_file("model.vcml")
result = vc.simulate(biomodel, "Simulation1")
result.plotter.plot_concentrations()
```

### Remote: connect, load from server, run on cluster

```python
import pyvcell.vcml as vc

session = vc.connect(login=True)
biomodel = session.load_biomodel("279851639")
store = session.run_sim(biomodel, "sim1")
```

### Chain simulations: use first run's output as next run's initial conditions

```python
result1 = vc.simulate(biomodel, "sim1")
species.init_conc = f"vcField('{result1.solver_output_dir.name}','s0',0.0,'Volume')"
result2 = vc.simulate(biomodel, "sim1")
```

### Parameter sweep

```python
for kf in [0.1, 1.0, 10.0]:
    model.set_parameter_value("r0.Kf", kf)
    result = vc.simulate(biomodel, "sim1")
    result.plotter.plot_concentrations()
```

## Architecture summary

| Layer             | Technology                          | Role                                                        |
| ----------------- | ----------------------------------- | ----------------------------------------------------------- |
| Python datamodels | Pydantic/dataclasses                | Model authoring, manipulation, essential VCell concepts     |
| libvcell          | Java via GraalVM native compilation | Validation, math generation, solver preprocessing           |
| Solvers           | C++ via pybind11/scikit-build-core  | Local finite volume, ODE, stochastic, rule-based simulation |
| VCell API         | OpenAPI generated client            | Remote simulation, model storage, result export             |
| Data access       | Zarr, N5/TensorStore, VTK           | Local and remote result retrieval                           |
| Visualization     | Matplotlib, PyVista, Trame          | 2D/3D plotting, animations, interactive Jupyter widgets     |
