"""Execute each guide notebook and fail if any cell raises an exception."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

NOTEBOOKS_DIR = Path(__file__).resolve().parents[2] / "docs" / "guides" / "notebooks"

REMOTE_NOTEBOOKS = {"remote-simulations"}

notebook_paths = sorted(NOTEBOOKS_DIR.glob("*.ipynb"))


@pytest.mark.parametrize(
    "notebook",
    notebook_paths,
    ids=[p.stem for p in notebook_paths],
)
def test_notebook_executes(notebook: Path, tmp_path: Path, request: pytest.FixtureRequest) -> None:
    """Run a notebook with nbconvert --execute and assert zero exit code."""
    if notebook.stem in REMOTE_NOTEBOOKS and not request.config.getoption("--run-remote", default=False):
        pytest.skip(f"{notebook.name} requires --run-remote flag (needs VCell auth)")
    output = tmp_path / notebook.name
    # Remote notebooks run full simulations on the VCell cluster — need longer timeout
    timeout = 600 if notebook.stem in REMOTE_NOTEBOOKS else 300
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
        timeout=timeout,
        # Render headless in the notebook kernel so no GUI window opens / blocks:
        # Agg for matplotlib, off-screen for pyvista/VTK.
        env={**__import__("os").environ, "MPLBACKEND": "Agg", "PYVISTA_OFF_SCREEN": "true"},
    )
    assert (
        result.returncode == 0
    ), f"Notebook {notebook.name} failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
