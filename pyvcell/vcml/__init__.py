"""Public API for ``pyvcell.vcml``.

Imports are lazy (PEP 562). Importing this package does **not** eagerly pull in
the heavy submodules (``session`` / ``vcml_remote`` / ``vcml_simulation`` /
``utils`` and their libvcell, requests, generated-REST-client, sympy and zarr
dependencies). Each public name is loaded from its defining submodule only on
first access, so importing just the datamodels — e.g. ``import
pyvcell.vcml.models_math`` or ``from pyvcell.vcml import MathDescription`` — stays
lightweight (only pydantic, plus numpy for the geometry model).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Eagerly visible to type checkers / IDEs; never executed at runtime.
    from pyvcell._internal.geometry import SegmentedImageGeometry
    from pyvcell.vcml.field import Field
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
    from pyvcell.vcml.vcml_reader import VcmlReader
    from pyvcell.vcml.vcml_remote import connect, logout
    from pyvcell.vcml.vcml_simulation import simulate
    from pyvcell.vcml.vcml_writer import VcmlWriter
    from pyvcell.vcml.workspace import get_workspace_dir, set_workspace_dir


# Each public name -> the submodule that defines (or re-exports) it. The submodule
# is imported lazily on first attribute access; lightweight datamodel submodules
# (models, models_geometry, models_math) never trigger the heavy ones.
_LAZY_IMPORTS: dict[str, str] = {
    "SegmentedImageGeometry": "pyvcell._internal.geometry",
    "Field": "pyvcell.vcml.field",
    **dict.fromkeys(
        [
            "Application",
            "Biomodel",
            "BoundaryType",
            "Compartment",
            "Kinetics",
            "KineticsParameter",
            "Model",
            "ModelParameter",
            "Reaction",
            "Simulation",
            "Species",
            "SpeciesMapping",
            "SpeciesReference",
            "SpeciesRefType",
            "VCMLDocument",
            "Version",
        ],
        "pyvcell.vcml.models",
    ),
    **dict.fromkeys(
        ["Geometry", "Image", "PixelClass", "SubVolume", "SubVolumeType", "SurfaceClass"],
        "pyvcell.vcml.models_geometry",
    ),
    **dict.fromkeys(
        [
            "Boundaries",
            "CompartmentSubDomain",
            "Constant",
            "Effect",
            "JumpCondition",
            "JumpProcess",
            "MathBoundaryType",
            "MathDescription",
            "MathFunction",
            "MathVariable",
            "MathVariableType",
            "MembraneSubDomain",
            "OdeEquation",
            "ParticleInitialCount",
            "ParticleJumpProcess",
            "ParticleProperties",
            "PdeEquation",
            "VariableInitialCount",
            "Velocity",
        ],
        "pyvcell.vcml.models_math",
    ),
    **dict.fromkeys(["SimulationJob", "VCellSession"], "pyvcell.vcml.session"),
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
    "VcmlReader": "pyvcell.vcml.vcml_reader",
    **dict.fromkeys(["connect", "logout"], "pyvcell.vcml.vcml_remote"),
    "simulate": "pyvcell.vcml.vcml_simulation",
    "VcmlWriter": "pyvcell.vcml.vcml_writer",
    **dict.fromkeys(["get_workspace_dir", "set_workspace_dir"], "pyvcell.vcml.workspace"),
}


def __getattr__(name: str) -> object:
    module_path = _LAZY_IMPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module_path), name)
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
