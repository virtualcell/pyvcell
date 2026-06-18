# Installation

## Requirements

- Python 3.11 or later

## Install from PyPI

```bash
pip install pyvcell
```

The base install is lightweight (the data models + VCML reader/writer). Heavy
features live behind optional extras — install the ones you need, or everything:

```bash
pip install "pyvcell[viz]"     # plotting / VTK / PyVista
pip install "pyvcell[all]"     # full feature set (solver, viz, remote, io, convert, native)
```

## Install for development (uv)

```bash
git clone https://github.com/virtualcell/pyvcell.git
cd pyvcell
uv sync --all-groups
```

## Verify the installation

```python
import pyvcell.vcml as vc
print("pyvcell imported successfully")
```

## Workspace directory

pyvcell stores simulation output in a **workspace directory**. By default this is `./workspace` relative to your current working directory. You can change it:

```python
import pyvcell.vcml as vc

# Check the current workspace
print(vc.get_workspace_dir())

# Set a custom workspace
vc.set_workspace_dir("/path/to/my/workspace")
```

The workspace directory is created automatically if it doesn't exist.

## Included visualization libraries

pyvcell bundles several visualization libraries, all installed automatically:

- **Matplotlib** — 2D plots and concentration time series
- **VTK / PyVista** — 3D volume rendering and mesh visualization
- **Trame** — Interactive browser-based 3D widgets (for Jupyter notebooks)

## Next steps

- [Quick Start](quickstart.md) — Load a model, simulate, and plot results
