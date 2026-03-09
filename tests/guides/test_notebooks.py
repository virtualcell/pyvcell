"""Execute each guide notebook and fail if any cell raises an exception."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

NOTEBOOKS_DIR = Path(__file__).resolve().parents[2] / "docs" / "guides" / "notebooks"

SKIP_NOTEBOOKS = {"remote-simulations"}

notebook_paths = sorted(NOTEBOOKS_DIR.glob("*.ipynb"))


@pytest.mark.parametrize(
    "notebook",
    notebook_paths,
    ids=[p.stem for p in notebook_paths],
)
def test_notebook_executes(notebook: Path, tmp_path: Path) -> None:
    """Run a notebook with nbconvert --execute and assert zero exit code."""
    if notebook.stem in SKIP_NOTEBOOKS:
        pytest.skip(f"{notebook.name} requires interactive auth and a live server")
    output = tmp_path / notebook.name
    result = subprocess.run(
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
        env={**__import__("os").environ, "MPLBACKEND": "Agg"},
    )
    assert result.returncode == 0, (
        f"Notebook {notebook.name} failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
