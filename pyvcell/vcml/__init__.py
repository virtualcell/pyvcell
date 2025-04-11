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


def load_antimony_file(antimony_file: PathLike[str] | str) -> Biomodel:
    import antimony  # ignore

    antimony_success = antimony.loadAntimonyFile(antimony_file)
    if antimony_success != -1:
        sbml_str = antimony.getSBMLString()
        return load_sbml_str(sbml_str)
    else:
        raise ValueError("Error loading model:", antimony.getLastError())


def to_antimony_str(
    bio_model: Biomodel, application_name: str | None = None, round_trip_validation: bool = True
) -> str:
    sbml_str = to_sbml_str(bio_model, application_name, round_trip_validation=round_trip_validation)
    import antimony

    antimony_success = antimony.loadSBMLString(sbml_str)
    if antimony_success != -1:
        antimony_str = str(antimony.getAntimonyString())
        return antimony_str
    else:
        raise ValueError("Error converting SBML to Antimony:", antimony.getLastError())


def write_antimony_file(bio_model: Biomodel, antimony_file: PathLike[str] | str) -> None:
    antimony_str = to_antimony_str(bio_model)
    with open(antimony_file, "w") as f:
        f.write(antimony_str)


def load_vcml_str(vcml_str: str) -> Biomodel:
    return VcmlReader.biomodel_from_str(vcml_str)


def load_vcml_file(vcml_file: PathLike[str] | str) -> Biomodel:
    return VcmlReader.biomodel_from_file(vcml_file)


def to_vcml_str(bio_model: Biomodel) -> str:
    vcml_document = VCMLDocument(biomodel=bio_model)
    vcml_str: str = VcmlWriter().write_vcml(document=vcml_document)
    return vcml_str


def write_vcml_file(bio_model: Biomodel, vcml_file: PathLike[str] | str) -> None:
    vcml_document = VCMLDocument(biomodel=bio_model)
    VcmlWriter.write_to_file(vcml_document=vcml_document, file_path=vcml_file)


def load_sbml_str(sbml_str: str) -> Biomodel:
    import libvcell

    with tempfile.TemporaryDirectory() as tempdir:
        vcml_path = Path(tempdir) / "model.vcml"
        vc_success, vc_errmsg = libvcell.sbml_to_vcml(sbml_content=sbml_str, vcml_file_path=vcml_path)
        if vc_success:
            return VcmlReader.biomodel_from_file(vcml_path=vcml_path)
        else:
            raise ValueError("Error loading model:", vc_errmsg)


def load_sbml_file(sbml_file: PathLike[str] | str) -> Biomodel:
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


def to_sbml_str(bio_model: Biomodel, application_name: str | None = None, round_trip_validation: bool = True) -> str:
    import libvcell

    if application_name is None:
        if len(bio_model.applications) == 0:
            raise ValueError("sbml export from biomodel needs a biomodel application")
        if len(bio_model.applications) > 1:
            raise ValueError("Application must have exactly one application")
        application_name = bio_model.applications[0].name
    elif application_name not in [app.name for app in bio_model.applications]:
        raise ValueError(f"Application '{application_name}' not found in biomodel")
    vcml_document = VCMLDocument(biomodel=bio_model)
    vcml_str: str = VcmlWriter().write_vcml(document=vcml_document)
    with tempfile.TemporaryDirectory() as tempdir:
        sbml_path = Path(tempdir) / "model.sbml"
        success, msg = libvcell.vcml_to_sbml(
            vcml_content=vcml_str,
            application_name=application_name,
            sbml_file_path=sbml_path,
            round_trip_validation=round_trip_validation,
        )
        if not success:
            raise ValueError("Error converting VCML to SBML:", msg)
        with open(sbml_path) as f:
            sbml_str = f.read()
        return sbml_str


def write_sbml_file(
    bio_model: Biomodel,
    sbml_file: PathLike[str] | str,
    application_name: str | None = None,
    round_trip_validation: bool = True,
) -> None:
    sbml_str = to_sbml_str(bio_model, application_name, round_trip_validation)
    with open(sbml_file, "w") as f:
        f.write(sbml_str)


def refresh_biomodel(bio_model: Biomodel) -> Biomodel:
    with tempfile.TemporaryDirectory() as tempdir:
        vcml_path = Path(tempdir) / "model.vcml"
        write_vcml_file(bio_model=bio_model, vcml_file=vcml_path)
        return VcmlReader.biomodel_from_file(vcml_path=vcml_path)
