"""Public API for ``pyvcell.vcml``.

The lightweight data layer is eager: the data models (``models``,
``models_geometry``, ``models_math``) and ``VcmlReader`` import with only the
core dependencies (pydantic, lxml, numpy, numexpr). Everything that needs a
heavy optional dependency — ``VcmlWriter``, ``Field``, ``SegmentedImageGeometry``,
the remote ``VCellSession`` / ``connect`` / ``simulate`` API, and the ``utils`` /
``workspace`` helpers — is imported lazily (PEP 562) on first access. If the
optional dependency is missing, the lazy import raises a clear error naming the
extra to install (e.g. ``pip install pyvcell[viz]``).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

# --- eager, lightweight: data models + VCML reader (core deps only) ---
from pyvcell.vcml.models import (
    Application,
    Biomodel,
    BoundaryType,
    Compartment,
    Kinetics,
    KineticsParameter,
    Model,
    ModelParameter,
    Reaction,
    Simulation,
    Species,
    SpeciesMapping,
    SpeciesReference,
    SpeciesRefType,
    VCMLDocument,
    Version,
)
from pyvcell.vcml.models_geometry import (
    Geometry,
    Image,
    PixelClass,
    SubVolume,
    SubVolumeType,
    SurfaceClass,
)
from pyvcell.vcml.models_math import (
    Boundaries,
    CompartmentSubDomain,
    Constant,
    Effect,
    JumpCondition,
    JumpProcess,
    MathBoundaryType,
    MathDescription,
    MathFunction,
    MathVariable,
    MathVariableType,
    MembraneSubDomain,
    OdeEquation,
    ParticleInitialCount,
    ParticleJumpProcess,
    ParticleProperties,
    PdeEquation,
    VariableInitialCount,
    Velocity,
)
from pyvcell.vcml.vcml_reader import VcmlReader

if TYPE_CHECKING:
    # Heavy names — eager only for type checkers / IDE autocomplete.
    from pyvcell._internal.geometry import SegmentedImageGeometry
    from pyvcell.vcml.field import Field
    from pyvcell.vcml.session import SimulationJob, VCellSession
    from pyvcell.vcml.utils import (
        field_data_refs,
        load_antimony_file,
        load_antimony_str,
        load_sbml_file,
        load_sbml_str,
        load_sbml_url,
        load_vcml_file,
        load_vcml_str,
        load_vcml_url,
        restore_stdout,
        suppress_stdout,
        to_antimony_str,
        to_sbml_str,
        to_vcml_str,
        update_biomodel,
        write_antimony_file,
        write_sbml_file,
        write_vcml_file,
    )
    from pyvcell.vcml.vcml_remote import connect, logout
    from pyvcell.vcml.vcml_simulation import cartesian_mesh_from_geometry, simulate
    from pyvcell.vcml.vcml_writer import VcmlWriter
    from pyvcell.vcml.workspace import get_workspace_dir, set_workspace_dir


# Heavy public name -> the submodule that defines it (imported on first access).
_LAZY_IMPORTS: dict[str, str] = {
    "SegmentedImageGeometry": "pyvcell._internal.geometry",
    "Field": "pyvcell.vcml.field",
    "VcmlWriter": "pyvcell.vcml.vcml_writer",
    **dict.fromkeys(["SimulationJob", "VCellSession"], "pyvcell.vcml.session"),
    **dict.fromkeys(["connect", "logout"], "pyvcell.vcml.vcml_remote"),
    **dict.fromkeys(["simulate", "cartesian_mesh_from_geometry"], "pyvcell.vcml.vcml_simulation"),
    **dict.fromkeys(["get_workspace_dir", "set_workspace_dir"], "pyvcell.vcml.workspace"),
    **dict.fromkeys(
        [
            "field_data_refs",
            "load_antimony_file",
            "load_antimony_str",
            "load_sbml_file",
            "load_sbml_str",
            "load_sbml_url",
            "load_vcml_file",
            "load_vcml_str",
            "load_vcml_url",
            "restore_stdout",
            "suppress_stdout",
            "to_antimony_str",
            "to_sbml_str",
            "to_vcml_str",
            "update_biomodel",
            "write_antimony_file",
            "write_sbml_file",
            "write_vcml_file",
        ],
        "pyvcell.vcml.utils",
    ),
}

# Missing optional top-level module -> the extra that provides it, for a clear hint.
_EXTRA_FOR_MODULE: dict[str, str] = {
    "libvcell": "native",
    "pyvcell_fvsolver": "solver",
    "fvsolver": "solver",
    "vtk": "viz",
    "pyvista": "viz",
    "matplotlib": "viz",
    "imageio": "viz",
    "trame": "viz",
    "trame_server": "viz",
    "trame_vtk": "viz",
    "trame_vuetify": "viz",
    "requests": "remote",
    "requests_oauth2client": "remote",
    "urllib3": "remote",
    "dateutil": "remote",
    "overrides": "remote",
    "tensorstore": "io",
    "zarr": "io",
    "h5py": "io",
    "orjson": "io",
    "typer": "io",
    "antimony": "convert",
    "libsbml": "convert",
    "sympy": "convert",
}


def __getattr__(name: str) -> object:
    module_path = _LAZY_IMPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        missing = (exc.name or "").split(".")[0]
        extra = _EXTRA_FOR_MODULE.get(missing)
        hint = f"pip install pyvcell[{extra}]" if extra else "pip install pyvcell[all]"
        raise ModuleNotFoundError(
            f"pyvcell.vcml.{name} requires the optional dependency '{missing}', which is not installed. "
            f"Install it with `{hint}`."
        ) from exc
    value = getattr(module, name)
    globals()[name] = value  # cache so __getattr__ is not consulted again for this name
    return value


def __dir__() -> list[str]:
    return sorted(__all__)


__all__ = [
    "Application",
    "Biomodel",
    "Boundaries",
    "BoundaryType",
    "Compartment",
    "CompartmentSubDomain",
    "Constant",
    "Effect",
    "Field",
    "Geometry",
    "Image",
    "JumpCondition",
    "JumpProcess",
    "Kinetics",
    "KineticsParameter",
    "MathBoundaryType",
    "MathDescription",
    "MathFunction",
    "MathVariable",
    "MathVariableType",
    "MembraneSubDomain",
    "Model",
    "ModelParameter",
    "OdeEquation",
    "ParticleInitialCount",
    "ParticleJumpProcess",
    "ParticleProperties",
    "PdeEquation",
    "PixelClass",
    "Reaction",
    "SegmentedImageGeometry",
    "Simulation",
    "SimulationJob",
    "Species",
    "SpeciesMapping",
    "SpeciesRefType",
    "SpeciesReference",
    "SubVolume",
    "SubVolumeType",
    "SurfaceClass",
    "VCMLDocument",
    "VCellSession",
    "VariableInitialCount",
    "VcmlReader",
    "VcmlWriter",
    "Velocity",
    "Version",
    "cartesian_mesh_from_geometry",
    "connect",
    "field_data_refs",
    "get_workspace_dir",
    "load_antimony_file",
    "load_antimony_str",
    "load_sbml_file",
    "load_sbml_str",
    "load_sbml_url",
    "load_vcml_file",
    "load_vcml_str",
    "load_vcml_url",
    "logout",
    "restore_stdout",
    "set_workspace_dir",
    "simulate",
    "suppress_stdout",
    "to_antimony_str",
    "to_sbml_str",
    "to_vcml_str",
    "update_biomodel",
    "write_antimony_file",
    "write_sbml_file",
    "write_vcml_file",
]
