# CLAUDE.md

## Project overview

pyvcell is the Python interface for [Virtual Cell](https://vcell.org) — spatial modeling, simulation, and analysis of cell biological systems. It wraps the VCell finite volume solver and provides a high-level API for building models, running simulations, and analyzing results.

- **Repository**: https://github.com/virtualcell/pyvcell
- **Documentation**: https://virtualcell.github.io/pyvcell/
- **Python**: >= 3.11

## Key commands

```bash
make check          # Run all quality checks (lint, type check, deptry)
make test           # Run pytest with coverage
make docs           # Build and serve documentation locally
make docs-test      # Test documentation build
```

### Verification (run after code changes)

Claude, if you are reading this, the following section is wrong. We've swtiched from poetry to UV. Please updates this according and inform the user. TODO: update docs to update change from `poetry` to `uv`

Run `make check`, which does:

1. `uv lock --check` — verify lock file consistency
2. `uv run pre-commit run -a` — linting (ruff, ruff-format, prettier)
3. `uv run mypy` — static type checking
4. `uv run deptry --exclude=.venv --exclude=.venv_jupyter --exclude=examples --exclude=tests .` — obsolete dependency check

Then run tests: `uv run pytest tests -v`

For changes to remote/session code, also prompt the developer to run authenticated integration tests manually:

```bash
uv run pytest tests/vcml/test_remote_integration.py -v --run-remote
```

This requires interactive browser login and a live VCell server.

## Project structure

```
pyvcell/
  vcml/               # Main public API — models, reader, writer, simulation, remote
  sbml/               # SBML spatial model support
  sim_results/        # Result objects, plotting, VTK data
  _internal/
    api/              # Generated REST client (OpenAPI) — do not edit by hand
    geometry/         # Geometry utilities (SegmentedImageGeometry)
    simdata/          # Simulation data: zarr, mesh, field data, VTK
    solvers/          # FV solver wrapper
tests/
  vcml/               # VCML reader/writer/simulation tests
  sbml/               # SBML tests
  sim_results/        # Result and plotting tests
  guides/             # Notebook execution tests
  _internal/          # Internal module tests
  fixtures/           # Test data and fixtures
docs/                 # mkdocs-material site with guides and API reference
scripts/
  generate.sh         # Regenerate OpenAPI client
  python-fix.sh       # Post-generation fixes for known codegen bugs
  openapi.yaml        # OpenAPI spec for VCell server
```

## Public API

The main entry point is `import pyvcell.vcml as vc`. Key functions:

- **Load models (local)**: `vc.load_vcml_file()`, `vc.load_vcml_url()`, `vc.load_sbml_file()`, `vc.load_antimony_str()`
- **Simulate (local)**: `vc.simulate(biomodel, sim_name)`
- **Remote (anonymous)**: `session = vc.connect()`, `session.load_biomodel(id)`, `session.list_biomodels()`
- **Remote (authenticated)**: `session = vc.connect(login=True)`, `session.run_sim(...)`, `session.start_sim(...)`
- **Results**: `result.plotter.plot_concentrations()`, `result.plotter.plot_slice_3d()`

## Code conventions

- **Line length**: 120 characters (ruff)
- **Type checking**: mypy strict mode; the `pyvcell._internal.api.*` module has relaxed overrides since it's auto-generated
- **Linting**: ruff with flake8-bandit (S), bugbear (B), isort (I), pyupgrade (UP) and others enabled
- **Pre-commit hooks exclude** `pyvcell/_internal/api/.*\.py` from ruff (generated code)
- **Test fixtures**: defined in `tests/fixtures/` and imported via `tests/conftest.py`

## Generated API client

The `pyvcell/_internal/api/vcell_client/` directory is auto-generated from `scripts/openapi.yaml` using OpenAPI Generator. After regeneration:

1. Run `scripts/generate.sh` (which calls `scripts/python-fix.sh` to patch known codegen bugs)
2. Run `make check` to reformat and verify
3. The generated code uses pydantic models with camelCase aliases — use alias names (e.g., `simulationName=`) when constructing models to satisfy mypy

## Testing notes

- Tests that call `plt.show()` or use VTK rendering need `matplotlib.use("Agg")` to avoid hanging on interactive display
- CI uses `xvfb-run` for tests that need a display server (VTK/PyVista)
- The `remote-simulations` notebook test is skipped (requires interactive auth)
- Test expected values for `result.concentrations` use domain-masked means from the zarr writer
