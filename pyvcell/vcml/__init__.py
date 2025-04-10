import logging
import tempfile
from os import PathLike
from pathlib import Path

from pyvcell.vcml.models import (
    Application,
    Biomodel,
    BoundaryType,
    Compartment,
    Geometry,
    Image,
    Kinetics,
    KineticsParameter,
    Model,
    ModelParameter,
    PixelClass,
    Reaction,
    Simulation,
    Species,
    SpeciesMapping,
    SpeciesReference,
    SpeciesRefType,
    SubVolume,
    SubVolumeType,
    SurfaceClass,
    VCMLDocument,
)
from pyvcell.vcml.vcml_reader import VcmlReader
from pyvcell.vcml.vcml_writer import VcmlWriter

__all__ = [
    "VCMLDocument",
    "VcmlReader",
    "VcmlWriter",
    "Biomodel",
    "Model",
    "ModelParameter",
    "Reaction",
    "Compartment",
    "Image",
    "Kinetics",
    "KineticsParameter",
    "PixelClass",
    "Species",
    "SpeciesReference",
    "SpeciesRefType",
    "Application",
    "Geometry",
    "SubVolume",
    "SubVolumeType",
    "SurfaceClass",
    "SpeciesMapping",
    "BoundaryType",
    "Application",
    "Simulation",
]


def load_antimony_str(antimony_str: str) -> Biomodel:
    import antimony  # type: ignore[import-untyped]

    antimony_success = antimony.loadAntimonyString(antimony_str)
    if antimony_success != -1:
        sbml_str = antimony.getSBMLString()
        sbml_str = sbml_str.replace("sboTerm", "metaid")
        logging.info(f"Hack - introduced a metaid in place of sboTerm to SBML string:\n{sbml_str}")
        return load_sbml_str(sbml_str)
    else:
        raise ValueError("Error loading model:", antimony.getLastError())


def load_antimony_file(antimony_file: PathLike[str]) -> Biomodel:
    import antimony  # ignore

    antimony_success = antimony.loadAntimonyFile(antimony_file)
    if antimony_success != -1:
        sbml_str = antimony.getSBMLString()
        return load_sbml_str(sbml_str)
    else:
        raise ValueError("Error loading model:", antimony.getLastError())


def load_sbml_file(sbml_file: PathLike[str]) -> Biomodel:
    import libvcell

    with tempfile.TemporaryDirectory() as tempdir:
        with open(sbml_file) as f:
            sbml_str = f.read()
        vcml_path = Path(tempdir) / "model.vcml"
        vc_success, vc_errmsg = libvcell.sbml_to_vcml(sbml_content=sbml_str, vcml_file_path=vcml_path)
        if vc_success:
            return VcmlReader.biomodel_from_file(vcml_path=vcml_path)
        else:
            raise ValueError("Error loading model:", vc_errmsg)


def load_sbml_str(sbml_str: str) -> Biomodel:
    import libvcell

    with tempfile.TemporaryDirectory() as tempdir:
        vcml_path = Path(tempdir) / "model.vcml"
        vc_success, vc_errmsg = libvcell.sbml_to_vcml(sbml_content=sbml_str, vcml_file_path=vcml_path)
        if vc_success:
            return VcmlReader.biomodel_from_file(vcml_path=vcml_path)
        else:
            raise ValueError("Error loading model:", vc_errmsg)


def write_vcml_file(bio_model: Biomodel, vcml_file: PathLike[str]) -> None:
    vcml_document = VCMLDocument(biomodel=bio_model)
    VcmlWriter.write_to_file(vcml_document=vcml_document, file_path=vcml_file)


def to_vcml_str(bio_model: Biomodel) -> str:
    vcml_document = VCMLDocument(biomodel=bio_model)
    vcml_str: str = VcmlWriter().write_vcml(document=vcml_document)
    return vcml_str


def refresh_biomodel(bio_model: Biomodel) -> Biomodel:
    with tempfile.TemporaryDirectory() as tempdir:
        vcml_path = Path(tempdir) / "model.vcml"
        write_vcml_file(bio_model=bio_model, vcml_file=vcml_path)
        return VcmlReader.biomodel_from_file(vcml_path=vcml_path)
