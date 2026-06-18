# Installation

## Requirements

- Python 3.12 or later

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

## Type checking

pyvcell ships a `py.typed` marker ([PEP 561](https://peps.python.org/pep-0561/)),
so type checkers (mypy, pyright) use its inline annotations when you import it —
e.g. `pyvcell.vcml.models_math.MathDescription` is fully typed.

If you type-check a project against pyvcell but **don't install all of its
optional extras**, your checker may follow into pyvcell's optional-dependency
modules and report `import-not-found` for deps you didn't install (`libvcell`,
`sympy`, …). Those aren't your bugs — they're code paths you don't use. Tell your
checker to use pyvcell's public types without checking its internals:

```toml
# pyproject.toml of the consuming project
[[tool.mypy.overrides]]
module = ["pyvcell.*"]
follow_imports = "silent"
```

`follow_imports = "silent"` keeps pyvcell's types flowing into your code (so your
own usage is still fully checked) while silencing diagnostics inside pyvcell's
optional-dependency modules. Alternatively, install the extras you use (or
`pyvcell[all]`) so those imports resolve.

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

## Visualization libraries

The visualization stack lives in the `viz` extra (`pip install "pyvcell[viz]"`, or `pyvcell[all]`):

- **Matplotlib** — 2D plots and concentration time series
- **VTK / PyVista** — 3D volume rendering and mesh visualization
- **Trame** — Interactive browser-based 3D widgets (for Jupyter notebooks)

## Next steps

- [Quick Start](quickstart.md) — Load a model, simulate, and plot results
