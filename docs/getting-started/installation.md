# Installation

## Requirements

- Python 3.11 or later

## Install from PyPI

```bash
pip install pyvcell
```

## Install with Poetry (for development)

```bash
git clone https://github.com/virtualcell/pyvcell.git
cd pyvcell
poetry install
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

## Optional dependencies

pyvcell includes visualization tools that depend on:

- **Matplotlib** — 2D plots and concentration time series
- **VTK / PyVista** — 3D volume rendering and mesh visualization
- **Trame** — Interactive browser-based 3D widgets (for Jupyter notebooks)

All of these are installed automatically with `pip install pyvcell`.

## Next steps

- [Quick Start](quickstart.md) — Load a model, simulate, and plot results
