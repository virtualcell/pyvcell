"""The data models + VCML reader must import with only the core dependencies.

Downstream consumers (e.g. vcell-fenics) import ``pyvcell.vcml.models_math`` and
``VcmlReader.biomodel_from_file`` with only pydantic + lxml + numpy + numexpr
installed; importing them must not drag in the solver / viz / remote / libvcell
stack.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

import pyvcell.vcml as vc

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "data" / "TinySpatialProject_Application0.vcml"

# Top-level modules that belong to the heavy optional extras.
_HEAVY = {
    "libvcell",
    "pyvcell_fvsolver",
    "vtk",
    "pyvista",
    "matplotlib",
    "imageio",
    "trame",
    "requests",
    "urllib3",
    "tensorstore",
    "zarr",
    "h5py",
    "antimony",
    "libsbml",
    "sympy",
}


def test_data_layer_import_pulls_no_heavy_deps() -> None:
    """In a fresh interpreter, importing the data models + reader (and reading a
    VCML file) must not import any heavy optional dependency."""
    code = (
        "import sys\n"
        "from pyvcell.vcml.models_math import MathDescription\n"
        "from pyvcell.vcml.models_geometry import Geometry\n"
        "from pyvcell.vcml import MathDescription, VcmlReader, Geometry, Biomodel\n"
        "bm = VcmlReader.biomodel_from_file(sys.argv[1])\n"
        f"heavy = sorted(m for m in sys.modules if m.split('.')[0] in {sorted(_HEAVY)!r})\n"
        "assert not heavy, 'heavy modules imported: ' + repr(heavy)\n"
        "print('ok')\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed args, sys.executable + literal code
        [sys.executable, "-c", code, str(FIXTURE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_missing_extra_raises_helpful_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A heavy name whose optional dependency is missing reports the extra to install."""

    def fake_import(name: str) -> object:
        raise ModuleNotFoundError("No module named 'vtk'", name="vtk")

    monkeypatch.setattr(vc, "importlib", types.SimpleNamespace(import_module=fake_import))
    # Call __getattr__ directly so the lazy path runs even if the name was cached.
    with pytest.raises(ModuleNotFoundError, match=r"pyvcell\[viz\]"):
        vc.__getattr__("SegmentedImageGeometry")


def test_unknown_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        vc.__getattr__("does_not_exist")
