"""Lint and optionally execute example notebooks.

Static checks (ruff) run on all notebooks by default.
Execution tests are split into tiers:

- Default: notebooks that run headless without auth or display server
- --run-interactive: notebooks requiring trame/display server
- --run-remote: notebooks requiring VCell server auth

Usage:
    poetry run pytest tests/examples/test_example_notebooks.py -v                    # lint all, execute safe ones
    poetry run pytest tests/examples/test_example_notebooks.py -v --run-interactive  # also run trame notebooks
    poetry run pytest tests/examples/test_example_notebooks.py -v --run-remote       # also run auth notebooks
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

NOTEBOOKS_DIR = Path(__file__).resolve().parents[2] / "examples" / "notebooks"

# Notebooks that need interactive trame/display server
INTERACTIVE_NOTEBOOKS = {"fielddata_trame", "widget"}

# Notebooks that need VCell server auth
REMOTE_NOTEBOOKS = {"_internal_vcell_publications", "_internal_n5_download_demo"}

# Notebooks that can't be executed in CI
NO_EXECUTE_NOTEBOOKS: set[str] = set()

notebook_paths = sorted(NOTEBOOKS_DIR.glob("*.ipynb"))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "interactive: requires trame/display server")
    config.addinivalue_line("markers", "remote: requires VCell server auth")


# ---------------------------------------------------------------------------
# Static lint checks (all notebooks)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "notebook",
    notebook_paths,
    ids=[p.stem for p in notebook_paths],
)
def test_notebook_lint(notebook: Path, tmp_path: Path) -> None:
    """Export notebook to .py and run mypy type checks."""
    # Export to Python script
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "script",
            "--output-dir",
            str(tmp_path),
            str(notebook),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"nbconvert failed for {notebook.name}:\n{result.stderr}"

    # Find the exported .py file
    py_files = list(tmp_path.glob("*.py"))
    assert len(py_files) == 1, f"Expected 1 .py file, got {len(py_files)}"
    py_file = py_files[0]

    # Run mypy (same approach as scripts/check_notebooks.sh)
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "mypy",
            "--ignore-missing-imports",
            str(py_file),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Filter out errors inherent to notebook-as-script conversion:
    # - top-level-await: valid in Jupyter kernels
    # - name-defined: Jupyter builtins like display, In
    # - union-attr: biomodel.model is Model | None, notebooks don't guard
    # - no-redef: notebooks reuse variable names across cells
    # - no-untyped-call: Jupyter builtins like display are untyped
    # - attr-defined on generated API code: not explicitly exported
    notebook_noise = {"top-level-await", "name-defined", "union-attr", "no-redef", "no-untyped-call"}
    errors = [
        line
        for line in result.stdout.strip().splitlines()
        if "error:" in line and not any(f"[{code}]" in line for code in notebook_noise)
    ]
    assert not errors, f"Type errors in {notebook.name}:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Execution checks (tiered)
# ---------------------------------------------------------------------------


def _should_execute(notebook_stem: str, request: pytest.FixtureRequest) -> None:
    """Skip notebooks based on their tier and available flags."""
    if notebook_stem in NO_EXECUTE_NOTEBOOKS:
        pytest.skip(f"{notebook_stem} requires local data files not available in CI")
    if notebook_stem in INTERACTIVE_NOTEBOOKS:
        if not request.config.getoption("--run-interactive", default=False):
            pytest.skip(f"{notebook_stem} requires --run-interactive flag (needs trame/display)")
    if notebook_stem in REMOTE_NOTEBOOKS:
        if not request.config.getoption("--run-remote", default=False):
            pytest.skip(f"{notebook_stem} requires --run-remote flag (needs VCell auth)")


@pytest.mark.parametrize(
    "notebook",
    notebook_paths,
    ids=[p.stem for p in notebook_paths],
)
def test_notebook_executes(notebook: Path, tmp_path: Path, request: pytest.FixtureRequest) -> None:
    """Run a notebook with nbconvert --execute and assert zero exit code."""
    _should_execute(notebook.stem, request)

    output = tmp_path / notebook.name
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--output",
            str(output),
            str(notebook),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, "MPLBACKEND": "Agg"},
    )
    assert (
        result.returncode == 0
    ), f"Notebook {notebook.name} failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
